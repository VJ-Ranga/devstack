from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QComboBox,
    QProgressBar,
    QScrollArea,
    QMessageBox,
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
        
        # Main dynamic layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        
        # Initialize sub-screens
        self._init_header()
        self._init_scroll_area()
        self._init_wizard_view()
        self._init_progress_view()
        
        # Show App Grid by default
        self.show_grid()

    def _init_header(self):
        self.header_layout = QVBoxLayout()
        self.header_layout.setSpacing(4)
        
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
        self.grid_layout.setSpacing(20)
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
        self.wizard_layout.setContentsMargins(25, 25, 25, 25)
        self.wizard_layout.setSpacing(16)
        
        # Back Button
        back_btn = QPushButton("← Return to App Store")
        back_btn.setObjectName("DefaultButton")
        back_btn.setFixedWidth(180)
        back_btn.clicked.connect(self.show_grid)
        self.wizard_layout.addWidget(back_btn)
        
        # Wizard Title
        self.wiz_title = QLabel("Install Options")
        self.wiz_title.setObjectName("SummaryTitle")
        self.wizard_layout.addWidget(self.wiz_title)
        
        # Dynamic inputs container
        self.inputs_container = QWidget()
        self.inputs_layout = QVBoxLayout(self.inputs_container)
        self.inputs_layout.setContentsMargins(0, 0, 0, 0)
        self.inputs_layout.setSpacing(12)
        self.wizard_layout.addWidget(self.inputs_container)
        
        # Action Buttons
        self.wiz_action_layout = QHBoxLayout()
        self.wiz_action_layout.setSpacing(12)
        
        self.wiz_install_btn = QPushButton("Execute One-Click Install")
        self.wiz_install_btn.setObjectName("PrimaryButton")
        self.wiz_install_btn.clicked.connect(self._run_installer)
        self.wiz_action_layout.addWidget(self.wiz_install_btn)
        
        self.wiz_cancel_btn = QPushButton("Cancel")
        self.wiz_cancel_btn.setObjectName("DefaultButton")
        self.wiz_cancel_btn.clicked.connect(self.show_grid)
        self.wiz_action_layout.addWidget(self.wiz_cancel_btn)
        self.wiz_action_layout.addStretch(1)
        
        self.wizard_layout.addLayout(self.wiz_action_layout)
        self.main_layout.addWidget(self.wizard_frame)

    def _init_progress_view(self):
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("Panel")
        self.progress_layout = QVBoxLayout(self.progress_frame)
        self.progress_layout.setContentsMargins(40, 40, 40, 40)
        self.progress_layout.setSpacing(20)
        self.progress_layout.setAlignment(Qt.AlignCenter)
        
        self.progress_title = QLabel("Installing Site...")
        self.progress_title.setObjectName("SummaryTitle")
        self.progress_title.setAlignment(Qt.AlignCenter)
        self.progress_layout.addWidget(self.progress_title)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_layout.addWidget(self.progress_bar)
        
        self.progress_msg = QLabel("Downloading official release archives...")
        self.progress_msg.setObjectName("BodyText")
        self.progress_msg.setAlignment(Qt.AlignCenter)
        self.progress_layout.addWidget(self.progress_msg)
        
        self.success_button = QPushButton("🚀 Open Site in Browser")
        self.success_button.setObjectName("PrimaryButton")
        self.success_button.setFixedWidth(240)
        self.success_button.clicked.connect(self._open_newly_installed_site)
        self.progress_layout.addWidget(self.success_button)
        
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
        
        # Clear existing dynamic inputs
        for i in reversed(range(self.inputs_layout.count())):
            self.inputs_layout.itemAt(i).widget().setParent(None)
            
        self.input_widgets = {}
        
        # Build dynamic fields
        for field in installer_class.get_inputs():
            row = QHBoxLayout()
            row.setSpacing(20)
            
            lbl = QLabel(field["label"])
            lbl.setObjectName("RowTitle")
            lbl.setFixedWidth(140)
            row.addWidget(lbl)
            
            inp = QLineEdit()
            inp.setText(field["default"])
            if field["type"] == "password":
                inp.setEchoMode(QLineEdit.Password)
            row.addWidget(inp, 1)
            
            self.input_widgets[field["key"]] = inp
            self.inputs_layout.addLayout(row)
            
        # Add PHP version chooser dynamically
        row = QHBoxLayout()
        row.setSpacing(20)
        
        lbl = QLabel("PHP Version")
        lbl.setObjectName("RowTitle")
        lbl.setFixedWidth(140)
        row.addWidget(lbl)
        
        self.php_select = QComboBox()
        # Discover all available PHP versions installed in stack root
        php_versions = discover_php_versions(self.main_window.get_stack_root())
        for php in php_versions:
            self.php_select.addItem(php["version"], php["folder"])
            
        row.addWidget(self.php_select, 1)
        self.inputs_layout.addLayout(row)

    def show_progress(self):
        self.scroll.hide()
        self.wizard_frame.hide()
        self.progress_frame.show()
        
        self.progress_bar.setValue(0)
        self.progress_msg.setText("Starting offline installation process...")
        self.success_button.hide()

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
        self.worker.finished.connect(self._on_install_done)
        self.worker.start()

    def _on_install_progress(self, message, percentage):
        self.progress_bar.setValue(percentage)
        self.progress_msg.setText(message)

    def _on_install_done(self, success, message):
        if success:
            self.progress_bar.setValue(100)
            self.progress_msg.setText(message)
            self.success_button.show()
        else:
            QMessageBox.critical(self, "Installation Failed", f"An error occurred:\n{message}")
            self.show_wizard(self.active_installer)

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
