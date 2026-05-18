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
    QMessageBox,
    QComboBox,
    QApplication,
)
from core.config import load_sites, load_settings, save_settings
from core.installer import discover_php_versions

class WebsitesTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("TabPage")
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)

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
        self.main_layout.addLayout(header_row)

        # 2. Scrollable Sites Compact List
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_content = QWidget()
        self.list_content.setObjectName("TabPage")
        self.list_layout = QVBoxLayout(self.list_content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1) # Bottom spacer to force list items upwards
        
        self.scroll.setWidget(self.list_content)
        self.main_layout.addWidget(self.scroll, 1)

        # Populate
        self.refresh_sites()

    def refresh_sites(self):
        # 0. Scan htdocs dynamically for auto-registration
        self._scan_and_import()

        # Clear previous list items (except the bottom stretch spacer)
        for i in reversed(range(self.list_layout.count() - 1)):
            item = self.list_layout.takeAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

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

            empty_desc = QLabel("Visit the App Store to download and extract WordPress, Laravel, or Custom PHP onto your DevStack!")
            empty_desc.setObjectName("MetaText")
            empty_desc.setStyleSheet("text-align: center;")
            empty_layout.addWidget(empty_desc, 0, Qt.AlignCenter)

            self.list_layout.insertWidget(0, empty_frame)
            return

        for i, site in enumerate(sites):
            row = SiteRow(site, self)
            self.list_layout.insertWidget(i, row)

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


class SiteRow(QFrame):
    def __init__(self, site, tab):
        super().__init__()
        self.site = site
        self.tab = tab
        self.setObjectName("Panel")
        
        # We only override the hover border-color, all other panel values (background, borders)
        # will cleanly inherit the application's default light/dark card style sheets natively!
        self.setStyleSheet("""
            QFrame#Panel:hover {
                border-color: #E55B3C;
            }
        """)
        self._setup_row()

    def _setup_row(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 1. App Glyph Icon
        icon_map = {
            "wordpress": "📝",
            "drupal": "💧",
            "laravel": "🌶️",
            "custom_php": "⚡"
        }
        app_icon = QLabel(icon_map.get(self.site.get("app_id"), "🌐"))
        app_icon.setStyleSheet("font-size: 18px;")
        layout.addWidget(app_icon)

        # 2. Site Title and Folder Name block
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        
        site_name = QLabel(self.site.get("site_title", "My Site"))
        site_name.setObjectName("RowTitle") # Natively styled bold title
        title_block.addWidget(site_name)

        folder_name = QLabel(f"htdocs/{self.site.get('folder')}")
        folder_name.setObjectName("MetaText") # Natively styled subtitle text
        title_block.addWidget(folder_name)
        layout.addLayout(title_block, 2)

        # 3. Core Engine & Configured PHP Badges
        cms_ver = self._detect_cms_version()
        app_badge = QLabel(f"{self.site.get('app_name', 'CMS')} ({cms_ver})")
        app_badge.setStyleSheet("""
            color: #E55B3C; 
            background-color: rgba(229, 91, 60, 0.08); 
            font-size: 10px; 
            font-weight: bold; 
            border-radius: 4px; 
            padding: 3px 6px; 
            border: none;
        """)
        layout.addWidget(app_badge)

        php_ver_lbl = QLabel(self.site.get("php_version", "PHP 8.2"))
        php_ver_lbl.setObjectName("MetaText")
        php_ver_lbl.setStyleSheet("""
            font-size: 10px; 
            background-color: rgba(130, 130, 130, 0.08); 
            border: 1px solid rgba(130, 130, 130, 0.15); 
            border-radius: 4px; 
            padding: 3px 6px;
        """)
        layout.addWidget(php_ver_lbl)

        # 4. Inline Console Credentials panel (only for CMS platforms like WordPress/Drupal)
        app_id = self.site.get("app_id", "custom_php")
        if app_id in ["wordpress", "drupal"]:
            creds_layout = QHBoxLayout()
            creds_layout.setContentsMargins(6, 2, 6, 2)
            creds_layout.setSpacing(6)

            user_val = self.site.get("admin_user", "admin")
            user_lbl = QLabel(f"👤 {user_val}")
            user_lbl.setStyleSheet("font-size: 10px; font-weight: bold;")
            creds_layout.addWidget(user_lbl)

            copy_user_btn = QPushButton("📋")
            copy_user_btn.setStyleSheet("border: none; background: transparent; font-size: 9px; max-width: 14px; padding: 0;")
            copy_user_btn.setCursor(Qt.PointingHandCursor)
            copy_user_btn.setToolTip("Copy Username")
            copy_user_btn.clicked.connect(lambda: self._copy_to_clipboard(user_val, "Username"))
            creds_layout.addWidget(copy_user_btn)

            # Divider
            div = QFrame()
            div.setFrameStyle(QFrame.VLine | QFrame.Plain)
            div.setStyleSheet("color: rgba(130,130,130,0.15); max-width: 1px;")
            creds_layout.addWidget(div)

            pass_val = self.site.get("admin_pass", "admin123")
            self.password_lbl = QLabel("🔑 ••••••••")
            self.password_lbl.setStyleSheet("font-size: 10px; font-weight: bold;")
            creds_layout.addWidget(self.password_lbl)

            reveal_btn = QPushButton("👁️")
            reveal_btn.setStyleSheet("border: none; background: transparent; font-size: 9px; max-width: 14px; padding: 0;")
            reveal_btn.setCursor(Qt.PointingHandCursor)
            reveal_btn.setToolTip("Reveal/Hide Password")
            reveal_btn.clicked.connect(self._toggle_password_visibility)
            creds_layout.addWidget(reveal_btn)

            copy_pass_btn = QPushButton("📋")
            copy_pass_btn.setStyleSheet("border: none; background: transparent; font-size: 9px; max-width: 14px; padding: 0;")
            copy_pass_btn.setCursor(Qt.PointingHandCursor)
            copy_pass_btn.setToolTip("Copy Password")
            copy_pass_btn.clicked.connect(lambda: self._copy_to_clipboard(pass_val, "Password"))
            creds_layout.addWidget(copy_pass_btn)

            creds_panel = QFrame()
            creds_panel.setObjectName("CredsBox")
            creds_panel.setStyleSheet("""
                QFrame#CredsBox {
                    background-color: rgba(130, 130, 130, 0.08); 
                    border: 1px solid rgba(130, 130, 130, 0.15); 
                    border-radius: 6px;
                }
            """)
            creds_panel.setLayout(creds_layout)
            layout.addWidget(creds_panel, 2)
        else:
            layout.addStretch(2)

        # 5. Compact Icon Action row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(6)

        open_btn = QPushButton("🌐 Open")
        open_btn.setObjectName("PrimaryButton")
        open_btn.setCursor(Qt.PointingHandCursor)
        action_layout.addWidget(open_btn)

        if app_id in ["wordpress", "drupal"]:
            admin_btn = QPushButton("🔑 Admin")
            admin_btn.setObjectName("DefaultButton")
            admin_btn.setCursor(Qt.PointingHandCursor)
            action_layout.addWidget(admin_btn)
            admin_btn.clicked.connect(self._open_admin)

        folder_btn = QPushButton("📁 Files")
        folder_btn.setObjectName("DefaultButton")
        folder_btn.setCursor(Qt.PointingHandCursor)
        action_layout.addWidget(folder_btn)

        delete_btn = QPushButton("🗑️")
        delete_btn.setObjectName("DangerButton")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setToolTip("Delete Website")
        delete_btn.clicked.connect(self._delete_site_handler)
        action_layout.addWidget(delete_btn)

        layout.addLayout(action_layout, 2)

        # Wire up open/files actions
        open_btn.clicked.connect(self._open_site)
        folder_btn.clicked.connect(self._open_folder)

    def _toggle_password_visibility(self):
        pass_val = self.site.get("admin_pass", "admin123")
        if self.password_lbl.text() == "🔑 ••••••••":
            self.password_lbl.setText(f"🔑 {pass_val}")
        else:
            self.password_lbl.setText("🔑 ••••••••")

    def _copy_to_clipboard(self, text, label):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.tab.main_window.statusBar().showMessage(f"{label} copied to clipboard!", 2000)

    def _detect_cms_version(self) -> str:
        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path = stack_root / "htdocs" / self.site.get("folder")
        
        if self.site.get("app_id") == "wordpress":
            version_file = site_path / "wp-includes" / "version.php"
            if version_file.exists():
                try:
                    content = version_file.read_text(encoding="utf-8")
                    for line in content.splitlines():
                        if "$wp_version =" in line:
                            return "v" + line.split("=")[1].strip(" ;'\"")
                except Exception:
                    pass
            return "WordPress core"
        elif self.site.get("app_id") == "drupal":
            return "core"
        elif self.site.get("app_id") == "laravel":
            return "v11.x"
        return "v1.0"

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

    def _delete_site_handler(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Delete Website")
        msg_box.setText(f"Are you sure you want to delete **{self.site.get('site_title', 'this site')}**?")
        msg_box.setInformativeText("Would you like to keep the website files on disk, or permanently destroy all files and database?")
        
        btn_keep_files = msg_box.addButton("Remove from Dashboard Only", QMessageBox.ActionRole)
        btn_destroy_all = msg_box.addButton("Permanently Delete Files and DB", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
        msg_box.setDefaultButton(btn_cancel)
        msg_box.exec()
        
        clicked_btn = msg_box.clickedButton()
        if clicked_btn == btn_cancel:
            return
            
        stack_root = Path(self.tab.main_window.get_stack_root())
        folder = self.site.get("folder")
        db_name = self.site.get("db_name", folder)
        
        if clicked_btn == btn_destroy_all:
            # 1. Drop MariaDB Database
            try:
                from core.installer import get_mysql_connection
                settings = self.tab.main_window.settings
                conn = get_mysql_connection(
                    str(stack_root),
                    settings.get("mysql_port", 3306)
                )
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`;")
                    cursor.close()
                    conn.close()
            except Exception as e:
                print(f"Error dropping database: {e}")
                
            # 2. Delete physical htdocs folder
            site_path = stack_root / "htdocs" / folder
            if site_path.exists() and site_path.is_dir():
                try:
                    import shutil
                    shutil.rmtree(str(site_path), ignore_errors=True)
                except Exception as e:
                    print(f"Error removing folder: {e}")
                    
        # 3. Delete registry entry
        from core.config import delete_site
        delete_site(folder)
        
        self.tab.main_window.statusBar().showMessage(f"Website '{self.site.get('site_title')}' has been successfully deleted.", 3000)
        self.tab.refresh_sites()
