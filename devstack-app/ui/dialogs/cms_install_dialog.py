import datetime
import re

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from core.cms_installer import CMS_NOTES, CMS_OPTIONS, CMSInstallWorker
from core.config import load_settings, save_site
from core.installer import discover_php_versions


# Platforms that require a running MariaDB instance
_DB_REQUIRED = {"wordpress", "drupal"}


class _MySQLStartWorker(QThread):
    """Starts MariaDB and waits up to 20 seconds for it to accept connections."""
    done = Signal(bool, str)  # (success, error_message)

    def __init__(self, stack_root: str):
        super().__init__()
        self.stack_root = stack_root

    def run(self):
        from core.service_manager import start, _is_running, _wait_for
        result = start(self.stack_root, "mysql")
        if not result.get("success"):
            self.done.emit(False, result.get("error", "Failed to start MariaDB."))
            return
        if _wait_for("mysqld.exe", 20):
            self.done.emit(True, "")
        else:
            self.done.emit(False, "MariaDB process started but did not become ready in time.")


class CMSInstallDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self._worker = None
        self.setWindowTitle("Install Website")
        self.setMinimumSize(560, 520)
        self.resize(580, 660)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        title_lbl = QLabel("Install Website")
        title_lbl.setObjectName("PageTitle")
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Download and configure a CMS or framework directly into your local stack."
        )
        sub_lbl.setObjectName("BodyText")
        sub_lbl.setWordWrap(True)
        layout.addWidget(sub_lbl)

        # ── Form ──────────────────────────────────────────────────────────
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Platform
        self.cms_combo = QComboBox()
        for opt in CMS_OPTIONS:
            self.cms_combo.addItem(opt["label"], opt["id"])
        self.cms_combo.currentIndexChanged.connect(self._on_cms_changed)
        form.addRow("Platform:", self.cms_combo)

        # Folder
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("e.g. mysite  (letters, numbers, - and _ only)")
        form.addRow("Folder Name:", self.folder_input)

        # Site title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. My Site")
        form.addRow("Site Title:", self.title_input)

        # Admin credentials (WordPress only — still recorded for all for the registry)
        self.user_input = QLineEdit()
        self.user_input.setText("admin")
        form.addRow("Admin Username:", self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setText("admin123")
        form.addRow("Admin Password:", self.pass_input)

        self.email_input = QLineEdit()
        self.email_input.setText("admin@localhost.local")
        form.addRow("Admin Email:", self.email_input)

        # PHP version
        self.php_combo = QComboBox()
        self._reload_php_versions()
        form.addRow("PHP Version:", self.php_combo)

        self._form = form
        layout.addLayout(form)

        # ── Per-platform note ─────────────────────────────────────────────
        self.note_frame = QFrame()
        self.note_frame.setObjectName("Panel")
        note_layout = QVBoxLayout(self.note_frame)
        note_layout.setContentsMargins(12, 8, 12, 8)
        self.note_label = QLabel()
        self.note_label.setObjectName("MetaText")
        self.note_label.setWordWrap(True)
        note_layout.addWidget(self.note_label)
        layout.addWidget(self.note_frame)

        # ── Progress section (hidden until install starts) ─────────────────
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("Panel")
        self.progress_frame.hide()
        prog_layout = QVBoxLayout(self.progress_frame)
        prog_layout.setSpacing(8)
        prog_layout.setContentsMargins(12, 10, 12, 10)

        self.prog_msg = QLabel("Installing...")
        self.prog_msg.setStyleSheet("font-size: 11px; font-weight: bold;")
        prog_layout.addWidget(self.prog_msg)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: rgba(0,0,0,0.05); border: none; "
            "border-radius: 6px; }"
            "QProgressBar::chunk { background-color: #E55B3C; border-radius: 6px; }"
        )
        prog_layout.addWidget(self.progress_bar)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(150)
        self.log_console.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #0b0b0f; color: #a9b7c6;"
            "  font-family: 'Consolas', 'Courier New', monospace; font-size: 10px;"
            "  border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 6px;"
            "}"
        )
        prog_layout.addWidget(self.log_console)
        layout.addWidget(self.progress_frame)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("DefaultButton")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.install_btn = QPushButton("Install")
        self.install_btn.setObjectName("PrimaryButton")
        self.install_btn.clicked.connect(self._start_install)
        btn_row.addWidget(self.install_btn)
        layout.addLayout(btn_row)

        # Trigger initial note
        self._on_cms_changed()

    def _on_cms_changed(self):
        cms_id = self.cms_combo.currentData()
        self.note_label.setText(CMS_NOTES.get(cms_id, ""))

        # Credential fields only used by WordPress; hide them for other platforms.
        # setUpdatesEnabled(False) prevents Qt from re-calculating minimum size on
        # every setVisible() call, which otherwise causes a window geometry loop.
        wp_only = cms_id == "wordpress"
        self.setUpdatesEnabled(False)
        for row_idx in (3, 4, 5):
            label_item = self._form.itemAt(row_idx, QFormLayout.LabelRole)
            field_item = self._form.itemAt(row_idx, QFormLayout.FieldRole)
            if label_item and label_item.widget():
                label_item.widget().setVisible(wp_only)
            if field_item and field_item.widget():
                field_item.widget().setVisible(wp_only)
        self.setUpdatesEnabled(True)
        self.adjustSize()

    def _reload_php_versions(self):
        stack_root = self.main_window.get_stack_root()
        versions   = discover_php_versions(stack_root)
        self.php_combo.clear()
        for php in versions:
            self.php_combo.addItem(php["version"], php["folder"])

    # ── install flow ──────────────────────────────────────────────────────

    def _start_install(self):
        folder = self.folder_input.text().strip()
        cms_id = self.cms_combo.currentData()

        # ── Validation ────────────────────────────────────────────────────
        if not folder:
            QMessageBox.warning(self, "Validation Error", "Folder name is required.")
            return
        if not re.fullmatch(r"[A-Za-z0-9_-]+", folder):
            QMessageBox.warning(
                self, "Validation Error",
                "Use only letters, numbers, underscores, or hyphens."
            )
            return
        if folder.lower() in {"dashboard", "assets", "phpmyadmin"}:
            QMessageBox.warning(self, "Validation Error", "This folder name is reserved.")
            return

        from pathlib import Path
        stack_root = self.main_window.get_stack_root()
        target = Path(stack_root) / "htdocs" / folder
        if target.exists():
            QMessageBox.warning(
                self, "Already Exists",
                f"htdocs/{folder} already exists. Choose a different folder name."
            )
            return

        site_title = self.title_input.text().strip() or folder.replace("_", " ").replace("-", " ").title()
        site_config = {
            "folder":      folder,
            "app_id":      cms_id,
            "app_name":    self.cms_combo.currentText(),
            "site_title":  site_title,
            "admin_user":  self.user_input.text().strip() or "admin",
            "admin_pass":  self.pass_input.text().strip() or "admin123",
            "admin_email": self.email_input.text().strip() or "admin@localhost.local",
            "php_folder":  self.php_combo.currentData() or "php",
            "php_version": self.php_combo.currentText() or "PHP 8.x",
            "db_name":     folder,
        }

        # ── MariaDB pre-flight for DB-dependent platforms ─────────────────
        if cms_id in _DB_REQUIRED and not self._is_mysql_running():
            reply = QMessageBox.question(
                self,
                "MariaDB Is Not Running",
                "This platform needs MariaDB to be running before installation can start.\n\n"
                "Start MariaDB now and continue automatically?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return
            self._start_mysql_then_install(stack_root, site_config)
            return

        self._run_install_worker(stack_root, site_config)

    def _is_mysql_running(self) -> bool:
        from core.service_manager import _is_running
        return _is_running("mysqld.exe")

    def _start_mysql_then_install(self, stack_root: str, site_config: dict):
        """Start MariaDB in background, then auto-proceed to install when ready."""
        self._lock_form(True)
        self.progress_frame.show()
        self.progress_bar.setValue(0)
        self.log_console.clear()
        self.prog_msg.setText("Starting MariaDB...")
        self._on_log("MariaDB is not running — starting it now...")
        self._on_log("This may take up to 20 seconds. Please wait.")

        self._mysql_starter = _MySQLStartWorker(stack_root)
        self._mysql_starter.done.connect(
            lambda ok, err: self._on_mysql_started(ok, err, stack_root, site_config)
        )
        self._mysql_starter.start()

    def _on_mysql_started(self, success: bool, error: str, stack_root: str, site_config: dict):
        # Do NOT null _mysql_starter here — C++ d->running may still be True at signal time
        if not success:
            self._lock_form(False)
            self.cancel_btn.setText("Close")
            self.prog_msg.setText("Could not start MariaDB.")
            self._on_log(f"[ERROR] {error}")
            QMessageBox.critical(
                self, "MariaDB Failed to Start",
                f"Could not start MariaDB:\n\n{error}\n\n"
                "Please start MariaDB manually from the Services tab and try again."
            )
            return

        self._on_log("MariaDB started successfully. Proceeding with installation...")
        self.main_window.notify_service_state_changed()
        self._run_install_worker(stack_root, site_config)

    def _run_install_worker(self, stack_root: str, site_config: dict):
        self._lock_form(True)
        self.progress_frame.show()
        self.progress_bar.setValue(0)
        if not self.log_console.toPlainText():
            self.log_console.clear()
        self.prog_msg.setText("Starting installation...")

        self._worker = CMSInstallWorker(stack_root, site_config)
        self._worker.progress.connect(self._on_progress)
        self._worker.log_emitted.connect(self._on_log)
        self._worker.finished.connect(lambda ok, msg: self._on_done(ok, msg, site_config))
        self._worker.start()

    def _lock_form(self, locked: bool):
        for w in (
            self.install_btn, self.cancel_btn, self.cms_combo,
            self.folder_input, self.title_input, self.user_input,
            self.pass_input, self.email_input, self.php_combo,
        ):
            w.setEnabled(not locked)

    def _on_progress(self, msg: str, pct: int):
        self.prog_msg.setText(msg)
        self.progress_bar.setValue(pct)

    def _on_log(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_console.appendPlainText(f"[{ts}] {msg}")

    def _on_done(self, success: bool, message: str, site_config: dict):
        self._lock_form(False)
        self.cancel_btn.setText("Close")

        if success:
            # Local dev tool — store the admin password so it can be shown later
            # in the Websites tab. sites.json is gitignored (never committed).
            save_site({
                **site_config,
                "installed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            self.prog_msg.setText("Installation complete!")
            if hasattr(self.main_window, "websites_tab"):
                self.main_window.websites_tab.refresh_sites()
            QMessageBox.information(self, "Installation Complete", message)
            self.accept()
        else:
            self.prog_msg.setText("Installation failed — see log for details.")
            QMessageBox.critical(self, "Installation Failed", message)
