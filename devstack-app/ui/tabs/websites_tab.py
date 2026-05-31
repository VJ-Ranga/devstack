import os
import webbrowser
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QMessageBox,
    QApplication,
)
from core.config import load_sites, load_settings
from ui.dialogs.cms_install_dialog import CMSInstallDialog


# Segoe MDL2 Assets codepoints
_ICON_FONT = '"Segoe Fluent Icons", "Segoe MDL2 Assets"'
_GLYPH = {
    "wordpress":   "",   # Clipboard / page
    "drupal":      "",   # Globe
    "laravel":     "",   # Code
    "custom_php":  "",   # FileCode
    "person":      "",   # Contact
    "lock":        "",   # Lock
    "copy":        "",   # Copy
    "view":        "",   # View
    "delete":      "",   # Delete
    "folder":      "",   # OpenInNewWindow / folder
    "open":        "",   # OpenInNewTab
    "admin":       "",   # Admin
}


def _glyph_label(char: str, size: int = 13, color: str = "") -> QLabel:
    lbl = QLabel(char)
    style = f'font-family: {_ICON_FONT}; font-size: {size}px; background: transparent;'
    if color:
        style += f' color: {color};'
    lbl.setStyleSheet(style)
    return lbl


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

        title = QLabel("Websites")
        title.setObjectName("PageTitle")
        self.main_layout.addWidget(title)

        subtitle = QLabel("Create local websites and view detected PHP/CMS/framework projects.")
        subtitle.setObjectName("BodyText")
        subtitle.setTextFormat(Qt.PlainText)  # prevent Qt auto-linking slashes as rich text
        self.main_layout.addWidget(subtitle)

        # Install panel
        create_panel = QFrame()
        create_panel.setObjectName("Panel")
        create_layout = QHBoxLayout(create_panel)
        create_layout.setContentsMargins(16, 12, 16, 12)
        create_layout.setSpacing(10)
        create_label = QLabel("Ready to add a new site?")
        create_label.setObjectName("RowTitle")
        create_layout.addWidget(create_label, 1)
        self.create_project_btn = QPushButton("+ Install Website")
        self.create_project_btn.setObjectName("PrimaryButton")
        self.create_project_btn.setCursor(Qt.PointingHandCursor)
        self.create_project_btn.clicked.connect(self._open_install_dialog)
        create_layout.addWidget(self.create_project_btn)
        self.main_layout.addWidget(create_panel)

        # Search bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search sites by name or type...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_sites)
        search_row.addWidget(self.search_input)
        self.main_layout.addLayout(search_row)

        # Scrollable site list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_content = QWidget()
        self.list_content.setObjectName("TabPage")
        self.list_layout = QVBoxLayout(self.list_content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_content)
        self.main_layout.addWidget(self.scroll, 1)

        self.refresh_sites()

    def refresh_sites(self):
        self._scan_and_import()
        for i in reversed(range(self.list_layout.count() - 1)):
            item = self.list_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()

        sites = load_sites()
        if not sites:
            empty = QFrame()
            empty.setObjectName("Panel")
            el = QVBoxLayout(empty)
            el.setContentsMargins(40, 40, 40, 40)
            el.setAlignment(Qt.AlignCenter)
            el.setSpacing(10)
            icon = _glyph_label("", size=36, color="rgba(130,130,130,0.4)")
            icon.setAlignment(Qt.AlignCenter)
            el.addWidget(icon)
            t = QLabel("No websites found yet.")
            t.setObjectName("SummaryTitle")
            t.setAlignment(Qt.AlignCenter)
            el.addWidget(t)
            d = QLabel("Create a website above. Existing PHP/CMS/framework folders are auto-detected.")
            d.setObjectName("MetaText")
            d.setTextFormat(Qt.PlainText)
            d.setAlignment(Qt.AlignCenter)
            el.addWidget(d)
            self.list_layout.insertWidget(0, empty)
            return

        for i, site in enumerate(sites):
            self.list_layout.insertWidget(i, SiteRow(site, self))

    def _filter_sites(self, text: str):
        for i in range(self.list_layout.count() - 1):
            item = self.list_layout.itemAt(i)
            w = item.widget() if item else None
            if w and isinstance(w, SiteRow):
                folder = w.site.get("folder", "").lower()
                app_name = w.site.get("app_name", "").lower()
                title = w.site.get("site_title", "").lower()
                q = text.lower()
                w.setVisible(not q or q in folder or q in app_name or q in title)

    def _open_install_dialog(self):
        dlg = CMSInstallDialog(self.main_window)
        dlg.exec()

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
            if not p.is_dir() or p.name in {"dashboard", "assets", "phpmyadmin"} or p.name in existing:
                continue
            app_id, app_name = "custom_php", "Custom PHP"
            if (p / "wp-config.php").exists() or (p / "wp-includes").exists():
                app_id, app_name = "wordpress", "WordPress"
            elif (p / "core" / "lib" / "Drupal.php").exists():
                app_id, app_name = "drupal", "Drupal"
            elif (p / "artisan").exists():
                app_id, app_name = "laravel", "Laravel"
            try:
                save_site({
                    "folder": p.name,
                    "app_id": app_id,
                    "app_name": app_name,
                    "admin_user": "admin",
                    "site_title": p.name.replace("_", " ").title(),
                    "php_folder": "php",
                    "php_version": "PHP 8.2 (Default)",
                    "installed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            except Exception as e:
                print(f"Error saving scanned site: {e}")

    def apply_density(self, density: str):
        from ui.styles import density_button_height, repolish
        h = density_button_height(density)
        self.create_project_btn.setFixedHeight(h)
        repolish(self.create_project_btn)
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), "apply_density"):
                item.widget().apply_density(density)


class SiteRow(QFrame):
    def __init__(self, site, tab):
        super().__init__()
        self.site = site
        self.tab = tab
        self.setObjectName("Panel")
        self.setStyleSheet("QFrame#Panel:hover { border-color: #E55B3C; }")
        self._password_visible = False
        self._setup_row()

    def _setup_row(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        app_id       = self.site.get("app_id", "custom_php")
        cms_needs_db = app_id in ("wordpress", "drupal")
        user_val     = self.site.get("admin_user", "admin")
        pass_val     = self.site.get("admin_pass")  # None if not stored (stripped after install)
        folder       = self.site.get("folder", "")
        self.password_lbl = None

        # ══════════════════════════════════════════════════════════════════
        # ROW 1:  [badge+path]  [credentials / no-creds]  <stretch>  [btns]
        # ══════════════════════════════════════════════════════════════════
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.setContentsMargins(0, 0, 0, 0)

        # ── LEFT: CMS badge + folder path + URL ───────────────────────
        cms_ver   = self._detect_cms_version()
        badge_txt = self.site.get("app_name", "PHP") + (f"  {cms_ver}" if cms_ver else "")
        cms_badge = QLabel(badge_txt)
        cms_badge.setStyleSheet(
            "color:#E55B3C; background:rgba(229,91,60,0.10);"
            "border:1px solid rgba(229,91,60,0.25); border-radius:10px;"
            "font-size:11px; font-weight:600; padding:2px 9px;"
        )
        cms_badge.setTextFormat(Qt.PlainText)

        folder_lbl = QLabel(f"htdocs/{folder}")
        folder_lbl.setObjectName("RowMeta")
        folder_lbl.setTextFormat(Qt.PlainText)

        # Build the site URL for display + copy
        _port = int(self.tab.main_window.settings.get("nginx_port", 80))
        _base = f"http://localhost:{_port}" if _port != 80 else "http://localhost"
        _suffix = "public/" if app_id == "laravel" else ""
        self._site_url = f"{_base}/{folder}/{_suffix}"
        url_lbl = QLabel(self._site_url)
        url_lbl.setStyleSheet("font-size:11px; color:#0078D4;")
        url_lbl.setTextFormat(Qt.PlainText)
        copy_url_btn = self._icon_btn(
            _GLYPH["copy"], "Copy URL",
            lambda u=self._site_url: self._copy_to_clipboard(u, "URL")
        )
        url_row = QHBoxLayout()
        url_row.setSpacing(2)
        url_row.setContentsMargins(0, 0, 0, 0)
        url_row.addWidget(url_lbl)
        url_row.addWidget(copy_url_btn)
        url_row.addStretch()

        left_col = QVBoxLayout()
        left_col.setSpacing(3)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.addWidget(cms_badge, 0, Qt.AlignLeft)
        left_col.addWidget(folder_lbl, 0, Qt.AlignLeft)
        left_col.addLayout(url_row)

        row1.addLayout(left_col)
        row1.addSpacing(10)

        # ── CENTRE: credentials tightly packed — NO stretch on this layout ─
        cred_row = QHBoxLayout()
        cred_row.setSpacing(6)
        cred_row.setContentsMargins(0, 0, 0, 0)

        if cms_needs_db:
            u_lbl = QLabel("User:")
            u_lbl.setObjectName("RowMeta")
            u_lbl.setTextFormat(Qt.PlainText)

            u_val = QLabel(user_val)
            u_val.setObjectName("RowTitle")
            u_val.setTextFormat(Qt.PlainText)

            copy_u = self._icon_btn(
                _GLYPH["copy"], "Copy username",
                lambda: self._copy_to_clipboard(user_val, "Username")
            )

            vsep = QFrame()
            vsep.setFrameShape(QFrame.VLine)
            vsep.setFixedWidth(1)
            vsep.setFixedHeight(16)
            vsep.setStyleSheet("background: rgba(0,0,0,0.15);")

            for w in (u_lbl, u_val, copy_u):
                cred_row.addWidget(w, 0, Qt.AlignVCenter)

            if pass_val is not None:
                p_lbl = QLabel("Pass:")
                p_lbl.setObjectName("RowMeta")
                p_lbl.setTextFormat(Qt.PlainText)

                self.password_lbl = QLabel(chr(0x2022) * 8)
                self.password_lbl.setObjectName("RowTitle")

                reveal_btn = self._icon_btn(
                    _GLYPH["view"], "Show / hide password",
                    self._toggle_password_visibility
                )
                copy_p = self._icon_btn(
                    _GLYPH["copy"], "Copy password",
                    lambda pv=pass_val: self._copy_to_clipboard(pv, "Password")
                )
                cred_row.addSpacing(10)
                cred_row.addWidget(vsep, 0, Qt.AlignVCenter)
                cred_row.addSpacing(10)
                for w in (p_lbl, self.password_lbl, reveal_btn, copy_p):
                    cred_row.addWidget(w, 0, Qt.AlignVCenter)
            else:
                not_stored = QLabel("Password not stored")
                not_stored.setStyleSheet("font-size:11px;color:#aaa;font-style:italic;")
                cred_row.addSpacing(10)
                cred_row.addWidget(vsep, 0, Qt.AlignVCenter)
                cred_row.addSpacing(10)
                cred_row.addWidget(not_stored, 0, Qt.AlignVCenter)

        else:
            no_cred = QLabel("No CMS database credentials")
            no_cred.setStyleSheet(
                "font-size:12px; color:rgba(100,120,100,0.75); font-style:italic;"
            )
            cred_row.addWidget(no_cred, 0, Qt.AlignVCenter)

        # Add cred_row WITHOUT stretch — widgets stay tightly packed together
        row1.addLayout(cred_row)

        # Stretch eats all leftover space between credentials and buttons
        row1.addStretch(1)

        # ── RIGHT: action buttons ──────────────────────────────────────
        self.open_btn = QPushButton("Open")
        self.open_btn.setObjectName("PrimaryButton")
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.clicked.connect(self._open_site)
        row1.addWidget(self.open_btn, 0, Qt.AlignVCenter)

        self.admin_btn = None
        if cms_needs_db:
            self.admin_btn = QPushButton("Admin")
            self.admin_btn.setObjectName("DefaultButton")
            self.admin_btn.setCursor(Qt.PointingHandCursor)
            self.admin_btn.clicked.connect(self._open_admin)
            row1.addWidget(self.admin_btn, 0, Qt.AlignVCenter)

        self.delete_btn = QPushButton()
        self.delete_btn.setObjectName("DangerButton")
        del_lbl = _glyph_label(_GLYPH["delete"], size=13)
        del_lbl.setAlignment(Qt.AlignCenter)
        del_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.delete_btn.setFixedWidth(32)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setToolTip("Delete website")
        self.delete_btn.clicked.connect(self._delete_site_handler)
        dl = QHBoxLayout(self.delete_btn)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.addWidget(del_lbl)
        row1.addWidget(self.delete_btn, 0, Qt.AlignVCenter)

        outer.addLayout(row1)

        # ══════════════════════════════════════════════════════════════════
        # ROW 2:  developer action buttons
        # ══════════════════════════════════════════════════════════════════
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.setContentsMargins(0, 0, 0, 0)
        row2.addStretch()

        self.terminal_btn = QPushButton("Terminal")
        self.terminal_btn.setObjectName("DefaultButton")
        self.terminal_btn.setToolTip("Open a terminal in this project folder")
        self.terminal_btn.setCursor(Qt.PointingHandCursor)
        self.terminal_btn.clicked.connect(self._open_terminal)
        row2.addWidget(self.terminal_btn)

        self.editor_btn = QPushButton("VS Code")
        self.editor_btn.setObjectName("DefaultButton")
        self.editor_btn.setToolTip("Open project in VS Code, Cursor, or PhpStorm")
        self.editor_btn.setCursor(Qt.PointingHandCursor)
        self.editor_btn.clicked.connect(self._open_in_editor)
        row2.addWidget(self.editor_btn)

        self.folder_btn = QPushButton("Files")
        self.folder_btn.setObjectName("DefaultButton")
        self.folder_btn.setCursor(Qt.PointingHandCursor)
        self.folder_btn.clicked.connect(self._open_folder)
        row2.addWidget(self.folder_btn)

        self.phpinfo_btn = QPushButton("PHP Info")
        self.phpinfo_btn.setObjectName("DefaultButton")
        self.phpinfo_btn.setToolTip("Open phpinfo page for this site")
        self.phpinfo_btn.setCursor(Qt.PointingHandCursor)
        self.phpinfo_btn.clicked.connect(self._open_phpinfo)
        row2.addWidget(self.phpinfo_btn)

        outer.addLayout(row2)

        self.apply_density(self.tab.main_window.settings.get("ui_density", "comfortable"))

    def _icon_btn(self, glyph: str, tooltip: str, callback) -> QPushButton:
        """Small icon-only button. Uses an embedded QLabel so MDL2 glyph font renders correctly."""
        btn = QPushButton()
        btn.setFixedSize(26, 26)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(0,0,0,0.07); }"
        )
        lbl = QLabel(glyph)
        lbl.setStyleSheet(
            f"font-family: {_ICON_FONT}; font-size: 13px; color: #9C9C9C; background: transparent;"
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        inner = QHBoxLayout(btn)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(lbl)
        btn.clicked.connect(callback)
        return btn

    def apply_density(self, density: str):
        from ui.styles import density_button_height, repolish
        h = density_button_height(density)
        for btn in (self.open_btn, self.admin_btn, self.folder_btn,
                    self.delete_btn,
                    self.terminal_btn, self.editor_btn, self.phpinfo_btn):
            if btn:
                btn.setFixedHeight(h)
                repolish(btn)

    def _toggle_password_visibility(self):
        if not self.password_lbl:
            return
        pass_val = self.site.get("admin_pass", "")
        self._password_visible = not self._password_visible
        self.password_lbl.setText(pass_val if self._password_visible else "••••••••")

    def _copy_to_clipboard(self, text, label):
        QApplication.clipboard().setText(text)
        self.tab.main_window.statusBar().showMessage(f"{label} copied to clipboard!", 2000)

    def _detect_cms_version(self) -> str:
        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path  = stack_root / "htdocs" / self.site.get("folder")
        if self.site.get("app_id") == "wordpress":
            vf = site_path / "wp-includes" / "version.php"
            if vf.exists():
                try:
                    for line in vf.read_text(encoding="utf-8").splitlines():
                        if "$wp_version =" in line:
                            return "v" + line.split("=")[1].strip(" ;'\"")
                except Exception:
                    pass
            return ""
        if self.site.get("app_id") == "drupal":
            return ""
        if self.site.get("app_id") == "laravel":
            return "v11.x"
        return ""

    def _open_site(self):
        port = int(self.tab.main_window.settings.get("nginx_port", 80))
        base = f"http://localhost:{port}" if port != 80 else "http://localhost"
        suffix = "public/" if self.site.get("app_id") == "laravel" else ""
        webbrowser.open(f"{base}/{self.site.get('folder')}/{suffix}")

    def _open_admin(self):
        port = int(self.tab.main_window.settings.get("nginx_port", 80))
        base = f"http://localhost:{port}" if port != 80 else "http://localhost"
        app_id = self.site.get("app_id")
        if app_id == "wordpress":
            url = f"{base}/{self.site.get('folder')}/wp-admin/"
        elif app_id == "drupal":
            url = f"{base}/{self.site.get('folder')}/user/login"
        else:
            url = f"{base}/phpmyadmin/"
        webbrowser.open(url)

    def _open_terminal(self):
        import subprocess
        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path  = stack_root / "htdocs" / self.site.get("folder")
        if not site_path.exists():
            QMessageBox.warning(self, "Not Found", str(site_path))
            return
        subprocess.Popen(
            ["cmd.exe", "/K", f"cd /d \"{site_path}\" && echo DevStack Terminal — {self.site.get('folder')}"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

    def _open_in_editor(self):
        import shutil as _shutil
        import subprocess
        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path  = str(stack_root / "htdocs" / self.site.get("folder"))
        for exe in ("code", "cursor", "phpstorm64", "phpstorm", "idea64"):
            if _shutil.which(exe):
                subprocess.Popen([exe, site_path])
                self.editor_btn.setText(exe.replace("64", "").title())
                return
        QMessageBox.information(
            self, "No Editor Found",
            "VS Code, Cursor, or PhpStorm was not found in PATH.\n\n"
            "Install one and make sure it's accessible from the command line."
        )

    def _open_phpinfo(self):
        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path  = stack_root / "htdocs" / self.site.get("folder")
        phpinfo_file = site_path / "_devstack_phpinfo.php"
        if not phpinfo_file.exists():
            try:
                phpinfo_file.write_text("<?php phpinfo(); ?>\n", encoding="utf-8")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create phpinfo file:\n{e}")
                return
        webbrowser.open(self._site_url.rstrip("/") + "/_devstack_phpinfo.php")

    def _open_folder(self):
        stack_root = Path(self.tab.main_window.get_stack_root())
        site_path  = stack_root / "htdocs" / self.site.get("folder")
        if site_path.exists():
            os.startfile(str(site_path))
        else:
            QMessageBox.warning(self, "Not Found", str(site_path))

    def _delete_site_handler(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Website")
        msg.setText(f"Delete  {self.site.get('site_title', 'this site')}?")
        msg.setInformativeText(
            "Remove from dashboard only, or permanently delete all files and the database?")
        btn_dash    = msg.addButton("Remove from Dashboard", QMessageBox.ActionRole)
        btn_destroy = msg.addButton("Delete Files + Database", QMessageBox.DestructiveRole)
        btn_cancel  = msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_cancel)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_cancel:
            return
        stack_root = Path(self.tab.main_window.get_stack_root())
        folder     = self.site.get("folder")
        if clicked == btn_destroy:
            try:
                from core.installer import get_mysql_connection
                s    = self.tab.main_window.settings
                conn = get_mysql_connection(str(stack_root), s.get("mysql_port", 3306))
                conn.execute(f"DROP DATABASE IF EXISTS `{self.site.get('db_name', folder)}`;")
            except Exception as e:
                print(f"DB drop error: {e}")
            site_path = stack_root / "htdocs" / folder
            if site_path.exists():
                import shutil
                shutil.rmtree(str(site_path), ignore_errors=True)
        from core.config import delete_site
        delete_site(folder)
        self.tab.main_window.statusBar().showMessage(
            f"'{self.site.get('site_title')}' deleted.", 3000)
        self.tab.refresh_sites()
