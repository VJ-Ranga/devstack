import os
import webbrowser
import re
from pathlib import Path
from PySide6.QtCore import Qt
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
    QLineEdit,
)
from core.config import load_sites, load_settings
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
        
        title = QLabel("Websites")
        title.setObjectName("PageTitle")
        title_block.addWidget(title)
        
        self.subtitle = QLabel("Create local websites and view detected PHP/CMS/framework projects.")
        self.subtitle.setObjectName("BodyText")
        title_block.addWidget(self.subtitle)
        header_row.addLayout(title_block, 1)
        self.main_layout.addLayout(header_row)

        # 2. Quick Create Panel (PHP only, no database setup)
        create_panel = QFrame()
        create_panel.setObjectName("Panel")
        create_layout = QHBoxLayout(create_panel)
        create_layout.setContentsMargins(12, 10, 12, 10)
        create_layout.setSpacing(10)

        create_label = QLabel("Create Website")
        create_label.setObjectName("RowTitle")
        create_layout.addWidget(create_label)

        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("project_folder_name")
        self.project_name_input.returnPressed.connect(self._create_php_project)
        create_layout.addWidget(self.project_name_input, 2)

        self.php_version_select = QComboBox()
        self._reload_php_versions()
        create_layout.addWidget(self.php_version_select, 2)

        self.create_project_btn = QPushButton("Create")
        self.create_project_btn.setObjectName("PrimaryButton")
        self.create_project_btn.setCursor(Qt.PointingHandCursor)
        self.create_project_btn.clicked.connect(self._create_php_project)
        create_layout.addWidget(self.create_project_btn)

        self.main_layout.addWidget(create_panel)

        # 3. Scrollable Sites Compact List
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
            empty_icon.setStyleSheet("font-size: 48px; color: rgba(130, 130, 130, 0.4);")
            empty_layout.addWidget(empty_icon, 0, Qt.AlignCenter)

            empty_title = QLabel("No websites found yet.")
            empty_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #555555;")
            empty_layout.addWidget(empty_title, 0, Qt.AlignCenter)

            empty_desc = QLabel("Create a website above. Existing PHP/CMS/framework folders are auto-detected.")
            empty_desc.setObjectName("MetaText")
            empty_desc.setStyleSheet("text-align: center;")
            empty_layout.addWidget(empty_desc, 0, Qt.AlignCenter)

            self.list_layout.insertWidget(0, empty_frame)
            return

        for i, site in enumerate(sites):
            row = SiteRow(site, self)
            self.list_layout.insertWidget(i, row)

    def _reload_php_versions(self):
        self.php_version_select.clear()
        php_versions = discover_php_versions(self.main_window.get_stack_root())
        for php in php_versions:
            self.php_version_select.addItem(php["version"], php["folder"])

    def _create_php_project(self):
        from core.config import save_site
        import datetime

        site_name = self.project_name_input.text().strip()
        if not site_name:
            QMessageBox.warning(self, "Validation Error", "Project folder name cannot be empty.")
            return
        if not re.fullmatch(r"[A-Za-z0-9_-]+", site_name):
            QMessageBox.warning(self, "Validation Error", "Use only letters, numbers, underscore, or hyphen.")
            return
        if site_name.lower() in {"dashboard", "assets", "phpmyadmin"}:
            QMessageBox.warning(self, "Validation Error", "This folder name is reserved.")
            return

        stack_root = Path(self.main_window.get_stack_root())
        htdocs_dir = stack_root / "htdocs"
        if not htdocs_dir.exists():
            QMessageBox.critical(self, "Path Error", f"htdocs folder was not found: {htdocs_dir}")
            return

        target_dir = htdocs_dir / site_name
        if target_dir.exists():
            QMessageBox.warning(self, "Already Exists", f"Project folder already exists: htdocs/{site_name}")
            return

        php_folder = self.php_version_select.currentData() or "php"
        php_label = self.php_version_select.currentText() or "PHP 8.2 (Default)"

        try:
            target_dir.mkdir(parents=True, exist_ok=False)
            index_php = target_dir / "index.php"
            index_php.write_text(
                """<?php
$title = 'My PHP Project';
?>
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title><?php echo $title; ?></title>
</head>
<body>
    <h1><?php echo $title; ?></h1>
    <p>Project created successfully.</p>
    <p>PHP Version: <?php echo PHP_VERSION; ?></p>
</body>
</html>
""",
                encoding="utf-8",
            )

            if php_folder != "php":
                port = 9000
                suffix = php_folder.replace("php", "").strip()
                if suffix.isdigit():
                    port = 9000 + int(suffix)
                htaccess_path = target_dir / ".htaccess"
                htaccess_path.write_text(
                    f"""# DevStack Directory PHP-FPM Version Selector Mapping
<FilesMatch \\.php$>
    SetHandler \"proxy:fcgi://127.0.0.1:{port}\"
</FilesMatch>
""",
                    encoding="utf-8",
                )

            save_site(
                {
                    "folder": site_name,
                    "app_id": "custom_php",
                    "app_name": "Custom PHP",
                    "admin_user": "admin",
                    "admin_pass": "admin123",
                    "site_title": site_name.replace("_", " ").replace("-", " ").title(),
                    "php_folder": php_folder,
                    "php_version": php_label,
                    "installed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        except Exception as e:
            QMessageBox.critical(self, "Create Failed", f"Could not create project:\n{e}")
            return

        self.project_name_input.clear()
        self.main_window.statusBar().showMessage(f"Created project: htdocs/{site_name}", 3000)
        self.refresh_sites()

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

    def apply_density(self, density: str):
        from ui.styles import density_button_height, repolish
        if hasattr(self, "create_project_btn"):
            h = density_button_height(density)
            self.create_project_btn.setFixedHeight(h)
            repolish(self.create_project_btn)
        if hasattr(self, "list_layout"):
            for i in range(self.list_layout.count()):
                item = self.list_layout.itemAt(i)
                if item and item.widget():
                    row = item.widget()
                    if hasattr(row, "apply_density"):
                        row.apply_density(density)


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

        # 1. App Glyph Icon using 100% reliable cross-platform standard symbols that always render beautifully
        icon_map = {
            "wordpress": "📝",
            "drupal": "💧",
            "laravel": "🌶️",
            "custom_php": "⚡"
        }
        glyph = icon_map.get(self.site.get("app_id"), "🌐")
        app_icon = QLabel(glyph)
        app_icon.setStyleSheet("""
            font-size: 16px;
            padding-right: 4px;
        """)
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

        self.php_version_combo = QComboBox()
        self.php_version_combo.setMinimumWidth(150)
        self._load_row_php_versions()
        layout.addWidget(self.php_version_combo)

        self.apply_php_btn = QPushButton("Apply PHP")
        self.apply_php_btn.setObjectName("DefaultButton")
        self.apply_php_btn.setCursor(Qt.PointingHandCursor)
        self.apply_php_btn.clicked.connect(self._apply_php_version)
        layout.addWidget(self.apply_php_btn)

        # 4. Inline Console Credentials panel (only for CMS-style platforms)
        app_id = self.site.get("app_id", "custom_php")
        if app_id in ["wordpress", "drupal"]:
            creds_layout = QHBoxLayout()
            creds_layout.setContentsMargins(6, 2, 6, 2)
            creds_layout.setSpacing(6)

            user_val = self.site.get("admin_user", "admin")
            user_lbl = QLabel(f"👤  {user_val}")
            user_lbl.setStyleSheet("font-size: 10px; font-weight: bold;")
            creds_layout.addWidget(user_lbl)

            copy_user_btn = QPushButton("📋")
            copy_user_btn.setStyleSheet("border: none; background: transparent; font-size: 10px; max-width: 14px; padding: 0;")
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
            self.password_lbl = QLabel("🔑  ••••••••")
            self.password_lbl.setStyleSheet("font-size: 10px; font-weight: bold;")
            creds_layout.addWidget(self.password_lbl)

            reveal_btn = QPushButton("👁️")
            reveal_btn.setStyleSheet("border: none; background: transparent; font-size: 10px; max-width: 14px; padding: 0;")
            reveal_btn.setCursor(Qt.PointingHandCursor)
            reveal_btn.setToolTip("Reveal/Hide Password")
            reveal_btn.clicked.connect(self._toggle_password_visibility)
            creds_layout.addWidget(reveal_btn)

            copy_pass_btn = QPushButton("📋")
            copy_pass_btn.setStyleSheet("border: none; background: transparent; font-size: 10px; max-width: 14px; padding: 0;")
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

        open_btn = QPushButton("Open")
        open_btn.setObjectName("PrimaryButton")
        open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn = open_btn
        action_layout.addWidget(open_btn)

        self.admin_btn = None
        if app_id in ["wordpress", "drupal"]:
            admin_btn = QPushButton("Admin")
            admin_btn.setObjectName("DefaultButton")
            admin_btn.setCursor(Qt.PointingHandCursor)
            self.admin_btn = admin_btn
            action_layout.addWidget(admin_btn)
            admin_btn.clicked.connect(self._open_admin)

        folder_btn = QPushButton("Files")
        folder_btn.setObjectName("DefaultButton")
        folder_btn.setCursor(Qt.PointingHandCursor)
        self.folder_btn = folder_btn
        action_layout.addWidget(folder_btn)

        delete_btn = QPushButton("🗑️")
        delete_btn.setObjectName("DangerButton")
        delete_btn.setStyleSheet("font-size: 11px;")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setToolTip("Delete Website")
        delete_btn.clicked.connect(self._delete_site_handler)
        self.delete_btn = delete_btn
        action_layout.addWidget(delete_btn)

        layout.addLayout(action_layout, 2)

        # Wire up open/files actions
        open_btn.clicked.connect(self._open_site)
        folder_btn.clicked.connect(self._open_folder)

        # Apply initial settings density
        from ui.styles import repolish
        self.apply_density(self.tab.main_window.settings.get("ui_density", "comfortable"))

    def apply_density(self, density: str):
        from ui.styles import density_button_height, repolish
        h = density_button_height(density)
        for btn in (self.open_btn, self.admin_btn, self.folder_btn, self.delete_btn, self.apply_php_btn):
            if btn:
                btn.setFixedHeight(h)
                repolish(btn)

    def _load_row_php_versions(self):
        stack_root = self.tab.main_window.get_stack_root()
        versions = discover_php_versions(stack_root)
        self.php_version_combo.clear()
        for php in versions:
            self.php_version_combo.addItem(php["version"], php["folder"])

        current_folder = self.site.get("php_folder", "php")
        idx = self.php_version_combo.findData(current_folder)
        if idx >= 0:
            self.php_version_combo.setCurrentIndex(idx)

    def _apply_php_version(self):
        from core.config import save_site

        selected_folder = self.php_version_combo.currentData() or "php"
        selected_label = self.php_version_combo.currentText() or "PHP 8.2 (Default)"

        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path = stack_root / "htdocs" / self.site.get("folder")
        if not site_path.exists():
            QMessageBox.warning(self, "Directory Not Found", f"The directory {site_path} does not exist.")
            return

        htaccess_path = site_path / ".htaccess"
        marker_start = "# DEVSTACK_PHP_SELECTOR_START"
        marker_end = "# DEVSTACK_PHP_SELECTOR_END"

        existing = ""
        if htaccess_path.exists():
            existing = htaccess_path.read_text(encoding="utf-8")

        block = ""
        if selected_folder != "php":
            port = 9000
            suffix = selected_folder.replace("php", "").strip()
            if suffix.isdigit():
                port = 9000 + int(suffix)
            block = (
                f"{marker_start}\n"
                "<FilesMatch \\.php$>\n"
                f"    SetHandler \"proxy:fcgi://127.0.0.1:{port}\"\n"
                "</FilesMatch>\n"
                f"{marker_end}\n"
            )

        pattern = re.compile(r"\n?# DEVSTACK_PHP_SELECTOR_START.*?# DEVSTACK_PHP_SELECTOR_END\n?", re.S)
        cleaned = re.sub(pattern, "\n", existing).strip()

        if block:
            content = (cleaned + "\n\n" + block).strip() + "\n"
            htaccess_path.write_text(content, encoding="utf-8")
        else:
            if cleaned:
                htaccess_path.write_text(cleaned + "\n", encoding="utf-8")
            elif htaccess_path.exists():
                htaccess_path.unlink()

        self.site["php_folder"] = selected_folder
        self.site["php_version"] = selected_label
        save_site(self.site)
        self.tab.main_window.statusBar().showMessage(
            f"Updated PHP version for {self.site.get('folder')} to {selected_label}", 3000
        )

    def _toggle_password_visibility(self):
        pass_val = self.site.get("admin_pass", "admin123")
        if self.password_lbl.text().endswith("••••••••"):
            self.password_lbl.setText(f"🔑  {pass_val}")
        else:
            self.password_lbl.setText(f"🔑  ••••••••")

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
        if self.site.get("app_id") == "drupal":
            return "core"
        elif self.site.get("app_id") == "laravel":
            return "v11.x"
        return "Plain PHP"

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
