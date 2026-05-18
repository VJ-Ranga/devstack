from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QComboBox, QProgressBar, QPlainTextEdit

from core.config import DEFAULT_SETTINGS, load_settings, save_settings
from ui.styles import density_button_height, repolish


class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
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
            box = QSpinBox()
            box.setRange(1, 65535)
            return box

        self.apache_port_input = port_spinbox()
        self.nginx_port_input = port_spinbox()
        self.php_port_input = port_spinbox()
        self.mysql_port_input = port_spinbox()
        ports_form.addRow("Apache Port", self.apache_port_input)
        ports_form.addRow("Nginx Port", self.nginx_port_input)
        ports_form.addRow("PHP Port", self.php_port_input)
        ports_form.addRow("MySQL Port", self.mysql_port_input)
        ports_layout.addLayout(ports_form)
        layout.addWidget(ports_panel)

        app_label, app_panel, app_layout = self._make_panel("APPLICATION")
        layout.addWidget(app_label)
        app_form = QFormLayout()
        app_form.setSpacing(8)
        self.refresh_interval_input = QSpinBox()
        self.refresh_interval_input.setRange(1, 60)
        self.refresh_interval_input.setSuffix(" seconds")
        self.ui_density_input = QComboBox()
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
        
        self.php_exec_input = QSpinBox()
        self.php_exec_input.setRange(1, 7200)
        self.php_exec_input.setSuffix(" seconds")
        
        php_ini_form.addRow("Memory Limit", self.php_mem_input)
        php_ini_form.addRow("Max Upload Limit", self.php_upload_input)
        php_ini_form.addRow("Max Post Size", self.php_post_input)
        php_ini_form.addRow("Execution Timeout", self.php_exec_input)
        
        self.save_php_ini_btn = QPushButton("Save and Apply PHP Limits")
        self.save_php_ini_btn.setObjectName("PrimaryButton")
        self.save_php_ini_btn.clicked.connect(self._save_php_ini_config)
        
        php_layout.addLayout(php_ini_form)
        php_layout.addWidget(self.save_php_ini_btn)
        
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
        self.dl_dismiss_btn.setFixedHeight(26)
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
        
        QMessageBox.information(
            self,
            "PHP Version Applied",
            f"Active PHP global interpreter has been switched to **{version_text}**!\n\n"
            "We will stop and restart all stack services now to apply these configurations.",
        )
        
        self._refresh_php_audit()
        self.main_window._refresh_all()
        from core.service_manager import restart
        restart(self.main_window.get_stack_root())

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
            "max_execution_time": "300"
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
        
        t_val = 300
        if audit['max_execution_time'].isdigit():
            t_val = int(audit['max_execution_time'])
        self.php_exec_input.setValue(t_val)

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
                new_lines.append(line)
                
            ini_path.write_text("\n".join(new_lines), encoding="utf-8")
            
            QMessageBox.information(
                self,
                "PHP Configuration Saved",
                "Your new **php.ini** directives were updated successfully!\n\n"
                "We will stop and restart all stack services now to apply the new PHP limits.",
            )
            
            self._refresh_php_audit()
            self.main_window._refresh_all()
            from core.service_manager import restart
            restart(stack_root)
            
        except Exception as e:
            QMessageBox.critical(self, "Error Saving php.ini", f"Failed to save settings: {e}")

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
        self.apache_port_input.setValue(settings.get("apache_port", 8088))
        self.nginx_port_input.setValue(settings.get("nginx_port", 80))
        self.php_port_input.setValue(settings.get("php_port", 9000))
        self.mysql_port_input.setValue(settings.get("mysql_port", 3306))
        self.refresh_interval_input.setValue(settings.get("auto_refresh_interval", 5))
        idx = self.ui_density_input.findData(settings.get("ui_density", "comfortable"))
        self.ui_density_input.setCurrentIndex(idx if idx >= 0 else 0)

    def _save_settings(self):
        stack = self.stack_root_input.text().strip()
        settings = {
            "stack_root": str(Path(stack).resolve()) if stack else stack,
            "apache_port": self.apache_port_input.value(),
            "nginx_port": self.nginx_port_input.value(),
            "php_port": self.php_port_input.value(),
            "mysql_port": self.mysql_port_input.value(),
            "auto_refresh_interval": self.refresh_interval_input.value(),
            "ui_density": self.ui_density_input.currentData(),
            "theme": self.main_window.settings.get("theme", "light"),
        }
        save_settings(settings)
        self.main_window.set_stack_root(settings["stack_root"])
        self.main_window.apply_settings(settings)
        QMessageBox.information(self, "Saved", "Settings saved.")

    def _reset_defaults(self):
        save_settings(DEFAULT_SETTINGS)
        self._load_settings()
        self.main_window.set_stack_root(DEFAULT_SETTINGS["stack_root"])
        self.main_window.apply_settings(DEFAULT_SETTINGS)
        QMessageBox.information(self, "Reset", "Default settings restored.")

    def apply_density(self, density: str):
        h = density_button_height(density)
        for btn in (self.browse_btn, self.save_btn, self.reset_btn):
            btn.setFixedHeight(h)
            repolish(btn)
