from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QComboBox,
    QProgressBar,
    QScrollArea,
    QMessageBox,
    QPlainTextEdit,
)
import webbrowser

from installers import ALL_INSTALLERS
from core.installer import InstallWorker, discover_php_versions
from ui.styles import repolish

class AppsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("TabPage")
        
        # Main dynamic layout (highly compact and tight margin)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(12)
        
        # Initialize sub-screens
        self._init_header()
        self._init_scroll_area()
        self._init_wizard_view()
        self._init_progress_view()
        
        # Show App Grid by default
        self.show_grid()

    def _init_header(self):
        self.header_layout = QVBoxLayout()
        self.header_layout.setSpacing(2)
        
        self.section_lbl = QLabel("PLUGGABLE ENGINE")
        self.section_lbl.setObjectName("SectionLabel")
        self.header_layout.addWidget(self.section_lbl)
        
        self.title_lbl = QLabel("App Store")
        self.title_lbl.setObjectName("PageTitle")
        self.header_layout.addWidget(self.title_lbl)
        
        self.sub_lbl = QLabel("Install CMS frameworks with one click. Setup local databases and PHP environments automatically.")
        self.sub_lbl.setObjectName("BodyText")
        self.header_layout.addWidget(self.sub_lbl)
        
        self.main_layout.addLayout(self.header_layout)

    def _init_scroll_area(self):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.grid_container = QWidget()
        self.grid_container.setObjectName("TabPage")
        self.grid_layout = QHBoxLayout(self.grid_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # Populate App Cards
        for installer_class in ALL_INSTALLERS:
            card = AppCard(installer_class, self)
            self.grid_layout.addWidget(card)
            
        self.scroll.setWidget(self.grid_container)
        self.main_layout.addWidget(self.scroll, 1)

    def _init_wizard_view(self):
        self.wizard_frame = QFrame()
        self.wizard_frame.setObjectName("Panel")
        self.wizard_layout = QVBoxLayout(self.wizard_frame)
        self.wizard_layout.setContentsMargins(20, 16, 20, 16)
        self.wizard_layout.setSpacing(12)
        
        # Back Button
        back_btn = QPushButton("← Return to App Store")
        back_btn.setObjectName("DefaultButton")
        back_btn.setFixedWidth(160)
        back_btn.setFixedHeight(28)
        back_btn.clicked.connect(self.show_grid)
        self.wizard_layout.addWidget(back_btn)
        
        # Wizard Title
        self.wiz_title = QLabel("Install Options")
        self.wiz_title.setObjectName("SummaryTitle")
        self.wizard_layout.addWidget(self.wiz_title)
        
        # Dynamic inputs container using standard QFormLayout
        self.inputs_container = QWidget()
        self.inputs_layout = QFormLayout(self.inputs_container)
        self.inputs_layout.setContentsMargins(0, 0, 0, 0)
        self.inputs_layout.setSpacing(8) # Compact spacing
        self.wizard_layout.addWidget(self.inputs_container)
        
        # Action Buttons Layout (to be nested dynamically in the form)
        self.wiz_action_layout = QHBoxLayout()
        self.wiz_action_layout.setSpacing(8)
        
        self.wiz_install_btn = QPushButton("Execute One-Click Install")
        self.wiz_install_btn.setObjectName("PrimaryButton")
        self.wiz_install_btn.setMinimumWidth(150)
        self.wiz_install_btn.setMaximumWidth(200)
        self.wiz_install_btn.setFixedHeight(28)
        self.wiz_install_btn.setCursor(Qt.PointingHandCursor)
        self.wiz_install_btn.clicked.connect(self._run_installer)
        self.wiz_action_layout.addWidget(self.wiz_install_btn)
        
        self.wiz_cancel_btn = QPushButton("Cancel")
        self.wiz_cancel_btn.setObjectName("DefaultButton")
        self.wiz_cancel_btn.setMinimumWidth(80)
        self.wiz_cancel_btn.setMaximumWidth(100)
        self.wiz_cancel_btn.setFixedHeight(28)
        self.wiz_cancel_btn.setCursor(Qt.PointingHandCursor)
        self.wiz_cancel_btn.clicked.connect(self.show_grid)
        self.wiz_action_layout.addWidget(self.wiz_cancel_btn)
        self.wiz_action_layout.addStretch(1)
        
        # Bottom vertical stretch to prevent vertical layout squishing!
        self.wizard_layout.addStretch(1)
        
        self.main_layout.addWidget(self.wizard_frame)

    def _init_progress_view(self):
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("Panel")
        self.progress_layout = QVBoxLayout(self.progress_frame)
        self.progress_layout.setContentsMargins(30, 30, 30, 30)
        self.progress_layout.setSpacing(16)
        self.progress_layout.setAlignment(Qt.AlignCenter)
        
        self.progress_title = QLabel("Installing Site...")
        self.progress_title.setObjectName("SummaryTitle")
        self.progress_title.setAlignment(Qt.AlignCenter)
        self.progress_layout.addWidget(self.progress_title)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setMaximumWidth(600)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_layout.addWidget(self.progress_bar, 0, Qt.AlignCenter)
        
        self.progress_msg = QLabel("Downloading official release archives...")
        self.progress_msg.setObjectName("BodyText")
        self.progress_msg.setAlignment(Qt.AlignCenter)
        self.progress_msg.setMaximumWidth(600)
        self.progress_layout.addWidget(self.progress_msg, 0, Qt.AlignCenter)
        
        # Live log terminal
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(200)
        self.log_console.setMaximumWidth(600)
        self.log_console.setStyleSheet("QPlainTextEdit { background-color: #1E1B18; color: #BF8E3B; border: 1px solid #E5E2DC; border-radius: 6px; font-family: Consolas, monospace; font-size: 11px; padding: 10px; }")
        self.progress_layout.addWidget(self.log_console, 0, Qt.AlignCenter)
        
        # Dynamic completion action buttons
        self.completion_layout = QHBoxLayout()
        self.completion_layout.setSpacing(12)
        self.completion_layout.setAlignment(Qt.AlignCenter)
        
        self.success_button = QPushButton("🚀 Open Site in Browser")
        self.success_button.setObjectName("PrimaryButton")
        self.success_button.setFixedWidth(180)
        self.success_button.setFixedHeight(28)
        self.success_button.clicked.connect(self._open_newly_installed_site)
        self.completion_layout.addWidget(self.success_button)
        
        self.retry_button = QPushButton("↩ Edit Settings")
        self.retry_button.setObjectName("PrimaryButton")
        self.retry_button.setFixedWidth(140)
        self.retry_button.setFixedHeight(28)
        self.retry_button.clicked.connect(lambda: self.show_wizard(self.active_installer))
        self.completion_layout.addWidget(self.retry_button)
        
        self.done_button = QPushButton("Return to App Store")
        self.done_button.setObjectName("DefaultButton")
        self.done_button.setFixedWidth(140)
        self.done_button.setFixedHeight(28)
        self.done_button.clicked.connect(self.show_grid)
        self.completion_layout.addWidget(self.done_button)
        
        self.progress_layout.addLayout(self.completion_layout)
        
        self.main_layout.addWidget(self.progress_frame)

    def show_grid(self):
        self.scroll.show()
        self.wizard_frame.hide()
        self.progress_frame.hide()

    def show_wizard(self, installer_class):
        self.scroll.hide()
        self.progress_frame.hide()
        self.wizard_frame.show()
        
        self.active_installer = installer_class
        self.wiz_title.setText(f"Install {installer_class.meta['name']}")
        
        # Clear QFormLayout dynamic rows cleanly
        while self.inputs_layout.rowCount():
            self.inputs_layout.removeRow(0)
            
        self.input_widgets = {}
        
        # Build responsive dynamic rows
        for field in installer_class.get_inputs():
            inp = QLineEdit()
            inp.setText(field["default"])
            
            if field["type"] == "password":
                inp.setEchoMode(QLineEdit.Password)
                
            self.input_widgets[field["key"]] = inp
            self.inputs_layout.addRow(field["label"], inp)
            
        # Add PHP version chooser dynamically
        self.php_select = QComboBox()
        
        php_versions = discover_php_versions(self.main_window.get_stack_root())
        for php in php_versions:
            self.php_select.addItem(php["version"], php["folder"])
            
        self.inputs_layout.addRow("PHP Version", self.php_select)
        
        # Add perfectly aligned action buttons directly as a form row
        self.inputs_layout.addRow("", self.wiz_action_layout)

    def show_progress(self):
        self.scroll.hide()
        self.wizard_frame.hide()
        self.progress_frame.show()
        
        self.progress_bar.setValue(0)
        self.progress_msg.setText("Starting offline installation process...")
        self.log_console.clear()
        self.success_button.hide()
        self.retry_button.hide()
        self.done_button.hide()

    def _run_installer(self):
        params = {}
        for key, inp in self.input_widgets.items():
            params[key] = inp.text().strip()
            
        # Validate parameters
        site_name = params.get("site_name", "").strip()
        if not site_name:
            QMessageBox.warning(self, "Validation Error", "Site folder name cannot be empty.")
            return
            
        self.newly_installed_site_folder = site_name
        self.show_progress()
        
        # Start background InstallWorker QThread
        php_folder = self.php_select.currentData()
        settings = self.main_window.settings
        db_port = int(settings.get("mysql_port", 3306))
        
        self.worker = InstallWorker(
            self.active_installer,
            self.main_window.get_stack_root(),
            params,
            php_folder,
            db_port
        )
        self.worker.progress.connect(self._on_install_progress)
        self.worker.log_emitted.connect(self._on_log_emitted)
        self.worker.finished.connect(self._on_install_done)
        self.worker.start()

    def _on_log_emitted(self, msg):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_console.appendPlainText(f"[{timestamp}] {msg}")

    def _on_install_progress(self, message, percentage):
        self.progress_bar.setValue(percentage)
        self.progress_msg.setText(message)

    def _on_install_done(self, success, message):
        if success:
            self.progress_bar.setValue(100)
            self.progress_msg.setText(message)
            self.success_button.show()
            self.retry_button.hide()
            self.done_button.show()
            
            # Record site metadata persistently
            try:
                from core.config import save_site
                import datetime
                php_folder = self.php_select.currentData()
                php_version = self.php_select.currentText()
                site_data = {
                    "folder": self.newly_installed_site_folder,
                    "app_id": self.active_installer.meta["id"],
                    "app_name": self.active_installer.meta["name"],
                    "admin_user": self.worker.params.get("admin_user", "admin"),
                    "admin_pass": self.worker.params.get("admin_pass", "admin123"),
                    "site_title": self.worker.params.get("site_title", "My DevStack Site"),
                    "php_folder": php_folder,
                    "php_version": php_version,
                    "installed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_site(site_data)
            except Exception as e:
                print(f"Error saving site: {e}")
        else:
            self.progress_msg.setText("Installation failed! Check console logs below.")
            self.log_console.appendPlainText(f"\n[ERROR] Installation failed:\n{message}")
            self.success_button.hide()
            self.retry_button.show()
            self.done_button.show()
            QMessageBox.critical(self, "Installation Failed", f"An error occurred:\n{message}")

    def _open_newly_installed_site(self):
        nginx_port = int(self.main_window.settings.get("nginx_port", 80))
        base = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"
        url = f"{base}/{self.newly_installed_site_folder}/"
        webbrowser.open(url)
        self.show_grid()


class AppCard(QFrame):
    def __init__(self, installer_class, apps_tab):
        super().__init__()
        self.installer_class = installer_class
        self.apps_tab = apps_tab
        self.setObjectName("QuickAccessCard")
        self.setFixedSize(220, 240)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Icon box
        icon_box = QFrame()
        icon_box.setObjectName("QuickAccessIconBox")
        icon_box.setFixedSize(48, 48)
        icon_layout = QVBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        icon_lbl = QLabel(installer_class.meta["icon"])
        icon_lbl.setStyleSheet("font-size: 24px;")
        icon_layout.addWidget(icon_lbl)
        layout.addWidget(icon_box)
        
        # Text details
        name_lbl = QLabel(installer_class.meta["name"])
        name_lbl.setObjectName("QuickAccessTitle")
        layout.addWidget(name_lbl)
        
        desc_lbl = QLabel(installer_class.meta["desc"])
        desc_lbl.setObjectName("QuickAccessSubtitle")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl, 1)
        
        # Category Badge
        cat_badge = QLabel(installer_class.meta["category"].upper())
        cat_badge.setObjectName("StatusBadge")
        cat_badge.setStyleSheet("color: #E55B3C; background-color: rgba(229, 91, 60, 0.08); font-size: 9px; font-weight: bold; border: none;")
        layout.addWidget(cat_badge)
        
        # Install Button
        install_btn = QPushButton("Install")
        install_btn.setObjectName("PrimaryButton")
        install_btn.setFixedHeight(28)
        install_btn.setCursor(Qt.PointingHandCursor)
        install_btn.clicked.connect(lambda: self.apps_tab.show_wizard(self.installer_class))
        layout.addWidget(install_btn)

    def enterEvent(self, event):
        self.setProperty("hover", "true")
        repolish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", "false")
        repolish(self)
        super().leaveEvent(event)
