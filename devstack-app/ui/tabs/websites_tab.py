import os
import webbrowser
import subprocess
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QGridLayout,
    QMessageBox,
    QComboBox,
    QApplication,
)
from core.config import load_sites, load_settings, save_settings
from core.installer import discover_php_versions
from ui.styles import density_button_height, repolish, set_status_badge

class WebsitesTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("TabPage")
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # 1. Header with Title & Active PHP Version Selector
        header_row = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(4)
        
        title = QLabel("My Local Websites")
        title.setObjectName("PageTitle")
        title_block.addWidget(title)
        
        self.subtitle = QLabel("Manage your active CMS sites, copy admin credentials, and browse local directories.")
        self.subtitle.setObjectName("BodyText")
        title_block.addWidget(self.subtitle)
        header_row.addLayout(title_block, 1)

        # Global Active PHP selector at the header
        self.php_selector_box = QFrame()
        self.php_selector_box.setObjectName("Panel")
        self.php_selector_box.setStyleSheet("background-color: rgba(0,0,0,0.02); border: 1px solid rgba(0,0,0,0.05); border-radius: 8px;")
        php_sel_layout = QHBoxLayout(self.php_selector_box)
        php_sel_layout.setContentsMargins(12, 8, 12, 8)
        php_sel_layout.setSpacing(8)

        php_lbl = QLabel("Global PHP:")
        php_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        php_sel_layout.addWidget(php_lbl)

        self.global_php_select = QComboBox()
        self.global_php_select.setFixedWidth(130)
        php_sel_layout.addWidget(self.global_php_select)

        self.apply_php_btn = QPushButton("Apply")
        self.apply_php_btn.setObjectName("PrimaryButton")
        self.apply_php_btn.setFixedWidth(60)
        self.apply_php_btn.clicked.connect(self._apply_global_php_version)
        php_sel_layout.addWidget(self.apply_php_btn)

        header_row.addWidget(self.php_selector_box)
        self.main_layout.addLayout(header_row)

        # 2. Scrollable Sites Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.grid_content = QWidget()
        self.grid_content.setObjectName("TabPage")
        self.grid_layout = QGridLayout(self.grid_content)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(16)
        self.grid_layout.setVerticalSpacing(16)
        
        self.scroll.setWidget(self.grid_content)
        self.main_layout.addWidget(self.scroll, 1)

        # Populate
        self.refresh_sites()

    def refresh_sites(self):
        # 0. Intelligent Auto-Scanner for existing htdocs directories
        self._scan_and_import()

        # Clear previous grid items
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Reload discovered PHP versions in selector
        self.global_php_select.clear()
        settings = load_settings()
        stack_root = settings.get("stack_root", "")
        php_versions = discover_php_versions(stack_root)
        active_folder = settings.get("active_php_folder", "php")
        
        for php in php_versions:
            self.global_php_select.addItem(php["version"], php["folder"])
            if php["folder"] == active_folder:
                idx = self.global_php_select.count() - 1
                self.global_php_select.setCurrentIndex(idx)

        # Load sites
        sites = load_sites()
        if not sites:
            empty_frame = QFrame()
            empty_frame.setObjectName("Panel")
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setContentsMargins(40, 40, 40, 40)
            empty_layout.setAlignment(Qt.AlignCenter)
            empty_layout.setSpacing(12)

            empty_icon = QLabel("🌐")
            empty_icon.setStyleSheet("font-size: 48px;")
            empty_layout.addWidget(empty_icon, 0, Qt.AlignCenter)

            empty_title = QLabel("No installed websites found.")
            empty_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #555555;")
            empty_layout.addWidget(empty_title, 0, Qt.AlignCenter)

            empty_desc = QLabel("Visit the App Store to download and extract WordPress or Drupal onto your DevStack in one-click!")
            empty_desc.setObjectName("MetaText")
            empty_desc.setStyleSheet("text-align: center;")
            empty_layout.addWidget(empty_desc, 0, Qt.AlignCenter)

            self.grid_layout.addWidget(empty_frame, 0, 0)
            return

        for i, site in enumerate(sites):
            card = SiteCard(site, self)
            self.grid_layout.addWidget(card, i // 2, i % 2)

    def _scan_and_import(self):
        settings = load_settings()
        stack_root = settings.get("stack_root", "")
        if not stack_root:
            return
            
        htdocs_dir = Path(stack_root) / "htdocs"
        if not htdocs_dir.exists():
            return
            
        from core.config import save_site
        import datetime
        
        existing = {s.get("folder") for s in load_sites()}
        
        for p in htdocs_dir.iterdir():
            if p.is_dir() and p.name not in ["dashboard", "assets", "phpmyadmin"] and p.name not in existing:
                app_id = "custom_php"
                app_name = "Custom PHP"
                
                if (p / "wp-config.php").exists() or (p / "wp-includes").exists():
                    app_id = "wordpress"
                    app_name = "WordPress"
                elif (p / "core" / "lib" / "Drupal.php").exists() or (p / "core" / "includes" / "bootstrap.inc").exists():
                    app_id = "drupal"
                    app_name = "Drupal"
                elif (p / "artisan").exists():
                    app_id = "laravel"
                    app_name = "Laravel"
                    
                site_data = {
                    "folder": p.name,
                    "app_id": app_id,
                    "app_name": app_name,
                    "admin_user": "admin",
                    "admin_pass": "admin123",
                    "site_title": p.name.replace("_", " ").title(),
                    "php_folder": "php",
                    "php_version": "PHP 8.2 (Default)",
                    "installed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                try:
                    save_site(site_data)
                except Exception as e:
                    print(f"Error saving scanned site: {e}")

    def _apply_global_php_version(self):
        folder = self.global_php_select.currentData()
        version_text = self.global_php_select.currentText()
        if not folder:
            return
            
        settings = load_settings()
        settings["active_php_folder"] = folder
        save_settings(settings)

        # Notify active main window settings update
        self.main_window.settings = settings
        self.main_window.apply_settings(settings)

        # Trigger database restart to apply new path
        QMessageBox.information(
            self,
            "PHP Version Changed",
            f"Active PHP environment switched to **{version_text}**!\n\n"
            "DevStack is applying these changes. We will stop and restart your services now to load the new binary.",
        )
        
        # Stop and start services dynamically in background worker
        self.main_window._refresh_all()
        from core.service_manager import restart
        restart(self.main_window.get_stack_root())


class SiteCard(QFrame):
    def __init__(self, site, tab):
        super().__init__()
        self.site = site
        self.tab = tab
        self.setObjectName("Panel")
        self._setup_card()

    def _setup_card(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Card Title Row
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        icon_map = {
            "wordpress": "📝",
            "drupal": "💧",
            "laravel": "🌶️",
            "custom_php": "⚡"
        }
        app_icon = QLabel(icon_map.get(self.site.get("app_id"), "🌐"))
        app_icon.setStyleSheet("font-size: 24px;")
        title_row.addWidget(app_icon)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        
        site_name = QLabel(self.site.get("site_title", "My Site"))
        site_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_block.addWidget(site_name)

        folder_name = QLabel(f"htdocs/{self.site.get('folder')}")
        folder_name.setObjectName("MetaText")
        folder_name.setStyleSheet("font-size: 11px;")
        title_block.addWidget(folder_name)
        title_row.addLayout(title_block, 1)

        # App type badge
        app_badge = QLabel(self.site.get("app_name", "CMS").upper())
        app_badge.setObjectName("StatusBadge")
        app_badge.setStyleSheet("color: #E55B3C; background-color: rgba(229, 91, 60, 0.08); font-size: 9px; font-weight: bold; border: none; padding: 2px 6px;")
        title_row.addWidget(app_badge, 0, Qt.AlignTop)

        layout.addLayout(title_row)

        # Separator line
        sep = QFrame()
        sep.setObjectName("SidebarSeparator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Details list
        details_layout = QGridLayout()
        details_layout.setSpacing(6)

        def add_detail_row(row_idx, label, value_widget):
            lbl = QLabel(label)
            lbl.setObjectName("MetaText")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            details_layout.addWidget(lbl, row_idx, 0)
            details_layout.addWidget(value_widget, row_idx, 1)

        # Admin Username with copy
        username_row = QHBoxLayout()
        username_row.setSpacing(4)
        username_val = QLabel(self.site.get("admin_user", "admin"))
        username_val.setStyleSheet("font-size: 11px;")
        username_row.addWidget(username_val, 1)
        
        copy_user_btn = QPushButton("📋")
        copy_user_btn.setStyleSheet("border: none; background: transparent; font-size: 10px; cursor: pointer; max-width: 20px;")
        copy_user_btn.clicked.connect(lambda: self._copy_to_clipboard(self.site.get("admin_user", "admin"), "Username"))
        username_row.addWidget(copy_user_btn)
        
        username_container = QWidget()
        username_container.setLayout(username_row)
        add_detail_row(0, "Admin Username:", username_container)

        # Admin Password with copy
        password_row = QHBoxLayout()
        password_row.setSpacing(4)
        
        self.password_val = QLabel("••••••••")
        self.password_val.setStyleSheet("font-size: 11px;")
        password_row.addWidget(self.password_val, 1)

        reveal_btn = QPushButton("👁️")
        reveal_btn.setStyleSheet("border: none; background: transparent; font-size: 10px; cursor: pointer; max-width: 20px;")
        reveal_btn.clicked.connect(self._toggle_password_visibility)
        password_row.addWidget(reveal_btn)

        copy_pass_btn = QPushButton("📋")
        copy_pass_btn.setStyleSheet("border: none; background: transparent; font-size: 10px; cursor: pointer; max-width: 20px;")
        copy_pass_btn.clicked.connect(lambda: self._copy_to_clipboard(self.site.get("admin_pass", "admin123"), "Password"))
        password_row.addWidget(copy_pass_btn)

        password_container = QWidget()
        password_container.setLayout(password_row)
        add_detail_row(1, "Admin Password:", password_container)

        # PHP & CMS Version details
        cms_ver = self._detect_cms_version()
        cms_ver_lbl = QLabel(cms_ver)
        cms_ver_lbl.setStyleSheet("font-size: 11px;")
        add_detail_row(2, "Core Version:", cms_ver_lbl)

        php_ver_lbl = QLabel(self.site.get("php_version", "PHP 8.2"))
        php_ver_lbl.setStyleSheet("font-size: 11px;")
        add_detail_row(3, "Configured PHP:", php_ver_lbl)

        layout.addLayout(details_layout)

        # Action Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        open_btn = QPushButton("🌐 Open Site")
        open_btn.setObjectName("PrimaryButton")
        open_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        open_btn.clicked.connect(self._open_site)
        btn_row.addWidget(open_btn, 1)

        admin_btn = QPushButton("🔑 Admin")
        admin_btn.setObjectName("DefaultButton")
        admin_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        admin_btn.clicked.connect(self._open_admin)
        btn_row.addWidget(admin_btn, 1)

        folder_btn = QPushButton("📁 Files")
        folder_btn.setObjectName("DefaultButton")
        folder_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(folder_btn, 1)

        layout.addLayout(btn_row)

    def _toggle_password_visibility(self):
        if self.password_val.text() == "••••••••":
            self.password_val.setText(self.site.get("admin_pass", "admin123"))
        else:
            self.password_val.setText("••••••••")

    def _copy_to_clipboard(self, text, label):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.tab.main_window.statusBar().showMessage(f"{label} copied to clipboard!", 2000)

    def _detect_cms_version(self) -> str:
        # Programmatically parse version file if exists
        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path = stack_root / "htdocs" / self.site.get("folder")
        
        if self.site.get("app_id") == "wordpress":
            version_file = site_path / "wp-includes" / "version.php"
            if version_file.exists():
                try:
                    content = version_file.read_text(encoding="utf-8")
                    for line in content.splitlines():
                        if "$wp_version =" in line:
                            return "WP v" + line.split("=")[1].strip(" ;'\"")
                except Exception:
                    pass
            return "WordPress core"
        elif self.site.get("app_id") == "drupal":
            return "Drupal core"
        elif self.site.get("app_id") == "laravel":
            return "Laravel Framework"
        return "Custom PHP"

    def _open_site(self):
        nginx_port = int(self.tab.main_window.settings.get("nginx_port", 80))
        base = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"
        suffix = "public/" if self.site.get("app_id") == "laravel" else ""
        url = f"{base}/{self.site.get('folder')}/{suffix}"
        webbrowser.open(url)

    def _open_admin(self):
        nginx_port = int(self.tab.main_window.settings.get("nginx_port", 80))
        base = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"
        
        if self.site.get("app_id") == "wordpress":
            url = f"{base}/{self.site.get('folder')}/wp-admin/"
        elif self.site.get("app_id") == "drupal":
            url = f"{base}/{self.site.get('folder')}/user/login"
        elif self.site.get("app_id") == "laravel":
            url = f"{base}/phpmyadmin/"
        else:
            url = f"{base}/phpmyadmin/"
            
        webbrowser.open(url)

    def _open_folder(self):
        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path = stack_root / "htdocs" / self.site.get("folder")
        if site_path.exists():
            os.startfile(str(site_path))
        else:
            QMessageBox.warning(self, "Directory Not Found", f"The directory {site_path} does not exist.")
