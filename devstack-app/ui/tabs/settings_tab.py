from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QComboBox, QProgressBar, QPlainTextEdit, QDialog, QCheckBox, QGridLayout

from core.config import DEFAULT_SETTINGS, load_settings, save_settings
from ui.styles import density_button_height, repolish


class PHPVersionSwitchWorker(QThread):
    finished = Signal(dict)

    def __init__(self, stack_root):
        super().__init__()
        self.stack_root = stack_root

    def run(self):
        from core.service_manager import restart
        res = restart(self.stack_root)
        self.finished.emit(res)


class GuardedSpinBox(QSpinBox):
    """SpinBox that only accepts scroll-wheel input when the mouse is physically over it.
    Prevents accidental value changes while scrolling the settings page."""
    def wheelEvent(self, event):
        if self.hasFocus() and self.underMouse():
            super().wheelEvent(event)
        else:
            event.ignore()


class GuardedComboBox(QComboBox):
    """ComboBox that only accepts scroll-wheel input when the mouse is physically over it."""
    def wheelEvent(self, event):
        if self.hasFocus() and self.underMouse():
            super().wheelEvent(event)
        else:
            event.ignore()


class SettingsTab(QWidget):
    COMMON_EXTENSIONS = [
        "curl", "gd", "mbstring", "mysqli", "openssl", "pdo_mysql", "zip", "xml", "dom", "json", "fileinfo", "exif", "intl", "ctype", "tokenizer", "bcmath", "soap", "sockets", "opcache"
    ]

    COMMON_EXTENSION_GROUPS = {
        "Core Web": ["curl", "openssl", "mbstring", "json", "ctype", "fileinfo"],
        "Database": ["mysqli", "pdo_mysql"],
        "Content/CMS": ["gd", "exif", "xml", "dom", "soap"],
        "Framework": ["tokenizer", "bcmath", "intl", "opcache"],
        "Optional": ["zip", "sockets"],
    }

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._ext_apply_worker = None
        self._ext_apply_context = ""
        self._switch_worker = None
        self._setup_ui()
        self._load_settings()
        self._refresh_php_audit()

    def _make_panel(self, label_text: str):
        label = QLabel(label_text)
        label.setObjectName("SectionLabel")
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        return label, panel, layout

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("TabPage")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Configure network ports, monitor system settings, and manage multiple PHP interpreters globally.")
        subtitle.setObjectName("BodyText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        stack_label, stack_panel, stack_layout = self._make_panel("STACK PATH")
        layout.addWidget(stack_label)
        stack_form = QFormLayout()
        stack_form.setSpacing(8)
        self.stack_root_input = QLineEdit()
        self.stack_root_input.setPlaceholderText("Path to devstack-template folder")
        browse_row = QHBoxLayout()
        browse_row.setSpacing(8)
        browse_row.addWidget(self.stack_root_input, 1)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("DefaultButton")
        self.browse_btn.clicked.connect(self._browse_stack_root)
        browse_row.addWidget(self.browse_btn)
        stack_form.addRow("Stack Root", browse_row)
        stack_layout.addLayout(stack_form)
        layout.addWidget(stack_panel)

        ports_label, ports_panel, ports_layout = self._make_panel("PORT CONFIGURATION")
        layout.addWidget(ports_label)
        ports_form = QFormLayout()
        ports_form.setSpacing(8)

        def port_spinbox():
            box = GuardedSpinBox()
            box.setRange(1, 65535)
            return box

        self.nginx_port_input = port_spinbox()
        self.php_port_input = port_spinbox()
        self.mysql_port_input = port_spinbox()
        ports_form.addRow("Nginx Port", self.nginx_port_input)
        ports_form.addRow("PHP Port", self.php_port_input)
        ports_form.addRow("MySQL Port", self.mysql_port_input)

        self.nginx_body_size_input = QLineEdit()
        self.nginx_body_size_input.setPlaceholderText("e.g. 128M")
        self.nginx_body_size_input.setToolTip("Nginx upload request limit. Examples: 64M, 128M, 256M.")
        ports_form.addRow("Nginx Upload Limit", self.nginx_body_size_input)
        ports_layout.addLayout(ports_form)
        layout.addWidget(ports_panel)

        app_label, app_panel, app_layout = self._make_panel("APPLICATION")
        layout.addWidget(app_label)
        app_form = QFormLayout()
        app_form.setSpacing(8)
        self.refresh_interval_input = GuardedSpinBox()
        self.refresh_interval_input.setRange(1, 60)
        self.refresh_interval_input.setSuffix(" seconds")
        self.ui_density_input = GuardedComboBox()
        self.ui_density_input.addItem("Comfortable", "comfortable")
        self.ui_density_input.addItem("Compact", "compact")
        app_form.addRow("Auto Refresh", self.refresh_interval_input)
        app_form.addRow("UI Density", self.ui_density_input)
        app_layout.addLayout(app_form)
        layout.addWidget(app_panel)

        # Brand New PHP Version and Settings panel
        php_lbl, php_panel, php_layout = self._make_panel("PHP RUNTIME MANAGEMENT")
        layout.addWidget(php_lbl)
        
        # PHP settings audit
        audit_lbl = QLabel("Edit active php.ini Vital Configurations:")
        audit_lbl.setStyleSheet("font-weight: bold; font-size: 11px; margin-top: 4px;")
        php_layout.addWidget(audit_lbl)

        php_ini_form = QFormLayout()
        php_ini_form.setSpacing(8)
        
        self.php_mem_input = QLineEdit()
        self.php_mem_input.setPlaceholderText("e.g. 256M")
        
        self.php_upload_input = QLineEdit()
        self.php_upload_input.setPlaceholderText("e.g. 64M")
        
        self.php_post_input = QLineEdit()
        self.php_post_input.setPlaceholderText("e.g. 64M")
        
        self.php_exec_input = GuardedSpinBox()
        self.php_exec_input.setRange(1, 7200)
        self.php_exec_input.setSuffix(" seconds")

        self.php_input_time_input = GuardedSpinBox()
        self.php_input_time_input.setRange(1, 7200)
        self.php_input_time_input.setSuffix(" seconds")
        
        self.display_errors_cb = QCheckBox("Show errors in browser (display_errors = On + E_ALL)")
        self.display_errors_cb.setToolTip(
            "Enables display_errors and sets error_reporting = E_ALL.\n"
            "Turn OFF for staging/production environments."
        )

        php_ini_form.addRow("Memory Limit", self.php_mem_input)
        php_ini_form.addRow("Max Upload Limit", self.php_upload_input)
        php_ini_form.addRow("Max Post Size", self.php_post_input)
        php_ini_form.addRow("Execution Timeout", self.php_exec_input)
        php_ini_form.addRow("Max Input Time", self.php_input_time_input)
        php_ini_form.addRow("Debug Mode", self.display_errors_cb)

        php_limits_hint = QLabel(
            "For large uploads, keep Max Post Size equal to or greater than Max Upload Limit. "
            "Nginx Upload Limit must also be high enough."
        )
        php_limits_hint.setObjectName("MetaText")
        php_limits_hint.setWordWrap(True)
        
        self.save_php_ini_btn = QPushButton("Save and Apply PHP Limits")
        self.save_php_ini_btn.setObjectName("PrimaryButton")
        self.save_php_ini_btn.clicked.connect(self._save_php_ini_config)
        
        php_layout.addLayout(php_ini_form)
        php_layout.addWidget(php_limits_hint)
        php_layout.addWidget(self.save_php_ini_btn)

        php_layout.addSpacing(6)

        ext_lbl = QLabel("PHP Extensions (active php.ini):")
        ext_lbl.setStyleSheet("font-weight: bold; font-size: 11px; margin-top: 4px;")
        php_layout.addWidget(ext_lbl)

        ext_row = QHBoxLayout()
        ext_row.setSpacing(8)
        self.php_ext_manage_btn = QPushButton("Open Extension Manager")
        self.php_ext_manage_btn.setObjectName("PrimaryButton")
        self.php_ext_manage_btn.clicked.connect(self._open_extension_manager)
        ext_row.addWidget(self.php_ext_manage_btn)
        php_layout.addLayout(ext_row)

        self.php_ext_enabled_lbl = QLabel("Enabled extensions: (loading)")
        self.php_ext_enabled_lbl.setObjectName("MetaText")
        self.php_ext_enabled_lbl.setWordWrap(True)
        php_layout.addWidget(self.php_ext_enabled_lbl)

        preset_hint = QLabel(
            "Common extension baseline: curl, gd, mbstring, mysqli, openssl, "
            "pdo_mysql, zip, xml, dom, json, fileinfo, exif, intl, ctype, tokenizer, "
            "bcmath, soap, sockets, opcache"
        )
        preset_hint.setObjectName("MetaText")
        preset_hint.setWordWrap(True)
        php_layout.addWidget(preset_hint)
        
        php_layout.addSpacing(6)
        
        # Discovered runtimes switch
        switch_form = QFormLayout()
        switch_form.setSpacing(8)
        self.active_php_combo = QComboBox()
        self.switch_php_btn = QPushButton("Apply Active Version")
        self.switch_php_btn.setObjectName("DefaultButton")
        self.switch_php_btn.clicked.connect(self._switch_php_version)
        
        switch_row = QHBoxLayout()
        switch_row.setSpacing(8)
        switch_row.addWidget(self.active_php_combo, 1)
        switch_row.addWidget(self.switch_php_btn)
        switch_form.addRow("Active Version", switch_row)
        php_layout.addLayout(switch_form)
        
        # Downloader block
        dl_lbl = QLabel("Download Stable PHP Version:")
        dl_lbl.setStyleSheet("font-weight: bold; font-size: 11px; margin-top: 8px;")
        php_layout.addWidget(dl_lbl)
        
        dl_form = QFormLayout()
        dl_form.setSpacing(8)
        self.stable_php_combo = QComboBox()
        from core.php_manager import STABLE_PHP_VERSIONS
        for ver in STABLE_PHP_VERSIONS:
            self.stable_php_combo.addItem(ver["version"], ver)
            
        self.dl_btn = QPushButton("Download and Install")
        self.dl_btn.setObjectName("PrimaryButton")
        self.dl_btn.clicked.connect(self._download_php_version)
        
        dl_row = QHBoxLayout()
        dl_row.setSpacing(8)
        dl_row.addWidget(self.stable_php_combo, 1)
        dl_row.addWidget(self.dl_btn)
        dl_form.addRow("Select Release", dl_row)
        php_layout.addLayout(dl_form)
        
        # Progress block for downloading
        self.dl_progress_frame = QFrame()
        self.dl_progress_frame.setObjectName("Panel")
        self.dl_progress_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; margin-top: 12px; padding: 12px;")
        self.dl_progress_frame.hide()
        
        dl_prog_layout = QVBoxLayout(self.dl_progress_frame)
        dl_prog_layout.setSpacing(8)
        
        self.dl_prog_msg = QLabel("Downloading PHP runtime package...")
        self.dl_prog_msg.setStyleSheet("font-size: 11px; font-weight: bold;")
        dl_prog_layout.addWidget(self.dl_prog_msg)
        
        self.dl_progress_bar = QProgressBar()
        self.dl_progress_bar.setFixedHeight(12)
        self.dl_progress_bar.setStyleSheet("QProgressBar { background-color: rgba(0,0,0,0.05); border: none; border-radius: 6px; text-align: center; } QProgressBar::chunk { background-color: #E55B3C; border-radius: 6px; }")
        dl_prog_layout.addWidget(self.dl_progress_bar)

        self.dl_log_console = QPlainTextEdit()
        self.dl_log_console.setReadOnly(True)
        self.dl_log_console.setFixedHeight(120)
        self.dl_log_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0b0b0f;
                color: #a9b7c6;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 6px;
            }
        """)
        dl_prog_layout.addWidget(self.dl_log_console)

        self.dl_dismiss_btn = QPushButton("Dismiss Console")
        self.dl_dismiss_btn.setObjectName("DefaultButton")
        self.dl_dismiss_btn.clicked.connect(self.dl_progress_frame.hide)
        self.dl_dismiss_btn.hide()
        dl_prog_layout.addWidget(self.dl_dismiss_btn)

        php_layout.addWidget(self.dl_progress_frame)
        
        layout.addWidget(php_panel)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._save_settings)
        button_row.addWidget(self.save_btn)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("DefaultButton")
        self.reset_btn.clicked.connect(self._reset_defaults)
        button_row.addWidget(self.reset_btn)
        layout.addLayout(button_row)
        layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def _switch_php_version(self):
        folder = self.active_php_combo.currentData()
        version_text = self.active_php_combo.currentText()
        if not folder:
            return
            
        settings = load_settings()
        settings["active_php_folder"] = folder
        save_settings(settings)
        
        self.main_window.settings = settings
        self.main_window.apply_settings(settings)
        
        self.switch_php_btn.setEnabled(False)
        self.switch_php_btn.setText("Restarting Stack...")
        
        self._refresh_php_audit()
        
        self._switch_worker = None  # drop previous (safe: guarded above)
        self._switch_worker = PHPVersionSwitchWorker(self.main_window.get_stack_root())
        self._switch_worker.finished.connect(self._on_switch_done)
        self._switch_worker.start()

    def _on_switch_done(self, result):
        # Do NOT null _switch_worker here — see RefreshWorker note in main_window.py
        self.switch_php_btn.setEnabled(True)
        self.switch_php_btn.setText("Apply Active Version")
        self.main_window._refresh_all()
        
        if result.get("success", False):
            self._refresh_php_extensions_audit()
            QMessageBox.information(
                self,
                "PHP Switch Success",
                "Stack services restarted and configured successfully under the new PHP runtime!",
            )
        else:
            QMessageBox.warning(
                self,
                "Partial Switch Success",
                f"PHP version switched, but some services failed to start:\n\n{result.get('error', 'Unknown service conflict')}",
            )

    def _refresh_php_audit(self):
        settings = load_settings()
        stack_root = settings.get("stack_root", "")
        active_folder = settings.get("active_php_folder", "php")
        
        # Load discovered runtimes in combo
        self.active_php_combo.clear()
        from core.installer import discover_php_versions
        php_versions = discover_php_versions(stack_root)
        for php in php_versions:
            self.active_php_combo.addItem(php["version"], php["folder"])
            if php["folder"] == active_folder:
                idx = self.active_php_combo.count() - 1
                self.active_php_combo.setCurrentIndex(idx)
                
        # Parse php.ini values
        ini_path = Path(stack_root) / active_folder / "php.ini"
        audit = {
            "memory_limit": "256M",
            "upload_max_filesize": "64M",
            "post_max_size": "64M",
            "max_execution_time": "300",
            "max_input_time": "300",
            "display_errors": "Off",
        }
        if ini_path.exists():
            try:
                content = ini_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith(";"):
                        continue
                    if "=" in line:
                        parts = line.split("=", 1)
                        key = parts[0].strip()
                        val = parts[1].strip()
                        if key in audit:
                            audit[key] = val
            except Exception:
                pass
                
        self.php_mem_input.setText(audit['memory_limit'])
        self.php_upload_input.setText(audit['upload_max_filesize'])
        self.php_post_input.setText(audit['post_max_size'])
        self.display_errors_cb.setChecked(audit['display_errors'].lower() in ("on", "1", "true"))
        
        t_val = 300
        if audit['max_execution_time'].isdigit():
            t_val = int(audit['max_execution_time'])
        self.php_exec_input.setValue(t_val)

        input_t_val = 300
        if audit['max_input_time'].isdigit():
            input_t_val = int(audit['max_input_time'])
        self.php_input_time_input.setValue(input_t_val)
        self._refresh_php_extensions_audit()

    def _get_active_php_ini_path(self) -> Path:
        settings = load_settings()
        stack_root = settings.get("stack_root", "")
        active_folder = settings.get("active_php_folder", "php")
        return Path(stack_root) / active_folder / "php.ini"

    def _read_enabled_extensions(self) -> list:
        ini_path = self._get_active_php_ini_path()
        if not ini_path.exists():
            return []
        enabled = []
        try:
            for line in ini_path.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith(";"):
                    continue
                if not s.lower().startswith("extension="):
                    continue
                ext_val = s.split("=", 1)[1].strip().strip('"').strip("'")
                ext_val = ext_val.replace("php_", "").replace(".dll", "")
                if ext_val:
                    enabled.append(ext_val.lower())
        except Exception:
            return []
        return sorted(set(enabled))

    def _refresh_php_extensions_audit(self):
        enabled = self._read_enabled_extensions()
        if not enabled:
            self.php_ext_enabled_lbl.setText("Enabled extensions: none detected")
            return
        self.php_ext_enabled_lbl.setText("Enabled extensions: " + ", ".join(enabled))

    def _save_php_ini_config(self):
        settings = load_settings()
        stack_root = settings.get("stack_root", "")
        active_folder = settings.get("active_php_folder", "php")
        ini_path = Path(stack_root) / active_folder / "php.ini"
        
        if not ini_path.exists():
            QMessageBox.critical(self, "Error", f"Active php.ini not found at {ini_path}")
            return
            
        mem = self.php_mem_input.text().strip()
        upload = self.php_upload_input.text().strip()
        post = self.php_post_input.text().strip()
        timeout = str(self.php_exec_input.value())
        max_input_time = str(self.php_input_time_input.value())
        display_errors_val = "On" if self.display_errors_cb.isChecked() else "Off"
        error_reporting_val = "E_ALL" if self.display_errors_cb.isChecked() else "E_ALL & ~E_DEPRECATED & ~E_STRICT"
        
        try:
            lines = ini_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            
            for line in lines:
                stripped = line.strip()
                if not stripped.startswith(";") and "=" in stripped:
                    parts = stripped.split("=", 1)
                    key = parts[0].strip()
                    if key == "memory_limit":
                        line = f"memory_limit = {mem}"
                    elif key == "upload_max_filesize":
                        line = f"upload_max_filesize = {upload}"
                    elif key == "post_max_size":
                        line = f"post_max_size = {post}"
                    elif key == "max_execution_time":
                        line = f"max_execution_time = {timeout}"
                    elif key == "max_input_time":
                        line = f"max_input_time = {max_input_time}"
                    elif key == "display_errors":
                        line = f"display_errors = {display_errors_val}"
                    elif key == "error_reporting":
                        line = f"error_reporting = {error_reporting_val}"
                new_lines.append(line)

            existing_keys = {
                line.split("=", 1)[0].strip()
                for line in new_lines
                if line.strip() and not line.strip().startswith(";") and "=" in line
            }
            if "max_input_time" not in existing_keys:
                new_lines.append(f"max_input_time = {max_input_time}")
                
            ini_path.write_text("\n".join(new_lines), encoding="utf-8")
            
            self._refresh_php_audit()
            self.main_window._refresh_all()
            self._restart_services_async(
                stack_root,
                "Applying PHP Limits",
                "PHP limits saved. Restarting services in background now.",
                "PHP limits applied and services restarted successfully.",
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error Saving php.ini", f"Failed to save settings: {e}")

    def _write_php_extensions(self, enabled_set: set):
        settings = load_settings()
        stack_root = settings.get("stack_root", "")
        active_folder = settings.get("active_php_folder", "php")
        ini_path = Path(stack_root) / active_folder / "php.ini"
        if not ini_path.exists():
            QMessageBox.critical(self, "Error", f"Active php.ini not found at {ini_path}")
            return
        try:
            lines = ini_path.read_text(encoding="utf-8").splitlines()
            out = []
            handled = set()
            for line in lines:
                raw = line.strip()
                if raw.lower().startswith("zend_extension=") or raw.lower().startswith(";zend_extension="):
                    body = raw.lstrip(";").split("=", 1)[1].strip().strip('"').strip("'")
                    name = body.lower().replace("php_", "").replace(".dll", "")
                    if name == "opcache":
                        if "opcache" in enabled_set:
                            out.append("zend_extension=opcache")
                        else:
                            out.append(";zend_extension=opcache")
                        handled.add("opcache")
                    else:
                        out.append(line)
                    continue
                if raw.lower().startswith("extension=") or raw.lower().startswith(";extension="):
                    body = raw.lstrip(";").split("=", 1)[1].strip().strip('"').strip("'")
                    name = body.lower().replace("php_", "").replace(".dll", "")
                    if name in enabled_set:
                        out.append(f"extension={name}")
                    else:
                        out.append(f";extension={name}")
                    handled.add(name)
                else:
                    out.append(line)
            for name in sorted(enabled_set - handled):
                if name == "opcache":
                    out.append("zend_extension=opcache")
                else:
                    out.append(f"extension={name}")
            ini_path.write_text("\n".join(out), encoding="utf-8")
            self._refresh_php_extensions_audit()
            self._restart_services_async(
                stack_root,
                "Applying Extensions",
                "Extension config saved. Restarting services in background now.",
                "Extensions applied and services restarted successfully.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update extensions: {e}")

    def _restart_services_async(self, stack_root: str, title_start: str, msg_start: str, msg_success: str):
        if self._ext_apply_worker and self._ext_apply_worker.isRunning():
            QMessageBox.information(self, "Please Wait", "A restart is already in progress.")
            return

        self._ext_apply_context = msg_success
        self._ext_apply_worker = None  # drop previous (safe: guarded above)
        self._ext_apply_worker = PHPVersionSwitchWorker(stack_root)
        self._ext_apply_worker.finished.connect(self._on_extension_restart_done)
        self._ext_apply_worker.start()

        QMessageBox.information(
            self,
            title_start,
            msg_start,
        )

    def _on_extension_restart_done(self, result):
        # Do NOT null _ext_apply_worker here — see RefreshWorker note in main_window.py
        self.main_window._refresh_all()
        if result.get("success", False):
            QMessageBox.information(self, "Restart Complete", self._ext_apply_context or "Services restarted successfully.")
        else:
            QMessageBox.warning(
                self,
                "Restart Warning",
                f"Extensions were saved, but some services failed to restart:\n\n{result.get('error', 'Unknown error')}",
            )

    def _open_extension_manager(self):
        settings = load_settings()
        stack_root = settings.get("stack_root", "")
        active_folder = settings.get("active_php_folder", "php")
        ext_dir = Path(stack_root) / active_folder / "ext"
        if not ext_dir.exists():
            QMessageBox.critical(self, "Error", f"Extension folder not found:\n{ext_dir}")
            return

        available = sorted({dll.stem.replace("php_", "").lower() for dll in ext_dir.glob("php_*.dll")})
        enabled = set(self._read_enabled_extensions())

        dlg = QDialog(self)
        dlg.setWindowTitle(f"PHP Extensions - {active_folder}")
        dlg.resize(760, 520)
        root = QVBoxLayout(dlg)
        top_info = QLabel(
            "Tick extensions to enable. Untick to disable. "
            "Save applies changes and restarts services."
        )
        top_info.setWordWrap(True)
        root.addWidget(top_info)

        group_lines = []
        for group, items in self.COMMON_EXTENSION_GROUPS.items():
            group_lines.append(f"{group}: " + ", ".join(items))
        common_info = QLabel("Most common extension sets\n" + "\n".join(group_lines))
        common_info.setObjectName("MetaText")
        common_info.setWordWrap(True)
        root.addWidget(common_info)

        frame = QFrame()
        grid = QGridLayout(frame)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)
        checks = {}
        cols = 4
        for i, name in enumerate(available):
            cb = QCheckBox(name)
            cb.setChecked(name in enabled)
            grid.addWidget(cb, i // cols, i % cols)
            checks[name] = cb

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        root.addWidget(scroll, 1)

        row = QHBoxLayout()
        common_btn = QPushButton("Apply Common Defaults")
        common_btn.setObjectName("DefaultButton")
        row.addWidget(common_btn)
        row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("DefaultButton")
        save_btn = QPushButton("Save")
        save_btn.setObjectName("PrimaryButton")
        row.addWidget(cancel_btn)
        row.addWidget(save_btn)
        root.addLayout(row)

        def _apply_common():
            common = set(self.COMMON_EXTENSIONS)
            for name, cb in checks.items():
                cb.setChecked(name in common)

        def _save():
            enabled_now = {n for n, cb in checks.items() if cb.isChecked()}
            self._write_php_extensions(enabled_now)
            dlg.accept()

        common_btn.clicked.connect(_apply_common)
        cancel_btn.clicked.connect(dlg.reject)
        save_btn.clicked.connect(_save)
        dlg.exec()

    def _download_php_version(self):
        ver_data = self.stable_php_combo.currentData()
        if not ver_data:
            return
            
        settings = load_settings()
        stack_root = settings.get("stack_root", "")
        
        # Disable buttons during download
        self.dl_btn.setEnabled(False)
        self.switch_php_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        
        self.dl_progress_frame.show()
        self.dl_progress_bar.setValue(0)
        self.dl_prog_msg.setText(f"Initializing download for {ver_data['version']}...")
        self.dl_log_console.clear()
        self.dl_dismiss_btn.hide()
        
        from core.php_manager import PHPDownloadWorker
        self.dl_worker = None  # drop any previous finished worker safely
        self.dl_worker = PHPDownloadWorker(stack_root, ver_data)
        self.dl_worker.progress.connect(self._on_dl_progress)
        self.dl_worker.log_emitted.connect(self._on_dl_log)
        self.dl_worker.finished.connect(self._on_dl_done)
        self.dl_worker.start()
        
    def _on_dl_log(self, msg):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.dl_log_console.appendPlainText(f"[{timestamp}] {msg}")

    def _on_dl_progress(self, msg, pct):
        self.dl_progress_bar.setValue(pct)
        self.dl_prog_msg.setText(msg)
        
    def _on_dl_done(self, success, message):
        self.dl_btn.setEnabled(True)
        self.switch_php_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        
        self.dl_dismiss_btn.show()
        
        if success:
            self.dl_prog_msg.setText("PHP Installed successfully! Check logs below.")
            QMessageBox.information(self, "PHP Installed", message)
            self._refresh_php_audit()
            if hasattr(self.main_window, "websites_tab"):
                self.main_window.websites_tab.refresh_sites()
        else:
            self.dl_prog_msg.setText("Installation failed! Check error details below.")
            QMessageBox.critical(self, "Installation Failed", message)

    def _browse_stack_root(self):
        path = QFileDialog.getExistingDirectory(self, "Select DevStack Root Folder", self.stack_root_input.text())
        if path:
            self.stack_root_input.setText(path)

    def _load_settings(self):
        settings = load_settings()
        self.stack_root_input.setText(settings.get("stack_root", ""))
        self.nginx_port_input.setValue(settings.get("nginx_port", 80))
        self.php_port_input.setValue(settings.get("php_port", 9000))
        self.mysql_port_input.setValue(settings.get("mysql_port", 3306))
        self.nginx_body_size_input.setText(settings.get("nginx_client_max_body_size", "128M"))
        self.refresh_interval_input.setValue(settings.get("auto_refresh_interval", 5))
        idx = self.ui_density_input.findData(settings.get("ui_density", "comfortable"))
        self.ui_density_input.setCurrentIndex(idx if idx >= 0 else 0)

    def _save_settings(self):
        stack = self.stack_root_input.text().strip()
        old = load_settings()
        ports_changed = any([
            self.nginx_port_input.value()   != old.get("nginx_port", 80),
            self.php_port_input.value()     != old.get("php_port", 9000),
            self.mysql_port_input.value()   != old.get("mysql_port", 3306),
        ])
        if ports_changed:
            reply = QMessageBox.question(
                self, "Confirm Port Changes",
                "You've changed one or more ports.\n\n"
                "All running services will be restarted automatically to apply the new ports.\n\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return

        old.update({
            "stack_root": str(Path(stack).resolve()) if stack else stack,
            "nginx_port": self.nginx_port_input.value(),
            "php_port": self.php_port_input.value(),
            "mysql_port": self.mysql_port_input.value(),
            "nginx_client_max_body_size": self.nginx_body_size_input.text().strip() or "128M",
            "auto_refresh_interval": self.refresh_interval_input.value(),
            "ui_density": self.ui_density_input.currentData(),
            "theme": self.main_window.settings.get("theme", "light"),
        })
        save_settings(old)
        self.main_window.set_stack_root(old["stack_root"])
        self.main_window.apply_settings(old)
        QMessageBox.information(self, "Saved", "Settings saved.")

    def _reset_defaults(self):
        save_settings(DEFAULT_SETTINGS)
        self._load_settings()
        self.main_window.set_stack_root(DEFAULT_SETTINGS["stack_root"])
        self.main_window.apply_settings(DEFAULT_SETTINGS)
        QMessageBox.information(self, "Reset", "Default settings restored.")

    def apply_density(self, density: str):
        h = density_button_height(density)
        buttons = (
            self.browse_btn,
            self.save_btn,
            self.reset_btn,
            getattr(self, "save_php_ini_btn", None),
            getattr(self, "switch_php_btn", None),
            getattr(self, "dl_btn", None),
            getattr(self, "dl_dismiss_btn", None),
            getattr(self, "php_ext_manage_btn", None),
        )
        for btn in buttons:
            if btn:
                btn.setFixedHeight(h)
                repolish(btn)
