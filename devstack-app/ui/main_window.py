import webbrowser

from PySide6.QtCore import QThread, QTimer, Signal, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QStackedWidget,
    QFrame,
    QLabel,
    QPushButton,
)

from core.config import load_settings
from core.status_reader import get_status
from core.version_reader import get_all_versions
from ui.styles import build_stylesheet, repolish
from ui.tabs.logs_tab import LogsTab
from ui.tabs.overview_tab import OverviewTab
from ui.tabs.services_tab import ServicesTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.websites_tab import WebsitesTab
from ui.widgets import SidebarButton
from ui.dialogs.customize_dialog import CustomizeUIDialog


class RefreshWorker(QThread):
    finished = Signal(dict, dict)

    def __init__(self, stack_root: str):
        super().__init__()
        self.stack_root = stack_root

    def run(self):
        self.finished.emit(get_status(self.stack_root), get_all_versions(self.stack_root))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self._refresh_worker = None
        self._pending_refresh = False
        self._closing = False
        self.setWindowTitle("DevStack Manager")
        self.resize(1000, 720)
        
        # Explicitly configure window icon to ensure taskbar renders it properly
        import os
        from PySide6.QtGui import QIcon
        ui_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(ui_dir)
        icon_path_ico = os.path.join(app_dir, "assets", "icon.ico")
        icon_path_png = os.path.join(app_dir, "assets", "icon.png")
        if os.path.exists(icon_path_ico):
            self.setWindowIcon(QIcon(icon_path_ico))
        elif os.path.exists(icon_path_png):
            self.setWindowIcon(QIcon(icon_path_png))
        
        # Load and apply custom screen size boundaries dynamically
        min_w = self.settings.get("min_width", 800)
        min_h = self.settings.get("min_height", 560)
        max_w = self.settings.get("max_width", 16777215)
        max_h = self.settings.get("max_height", 16777215)
        self.setMinimumSize(min_w, min_h)
        if max_w < 16777215 and max_h < 16777215:
            self.setMaximumSize(max_w, max_h)
        else:
            self.setMaximumSize(16777215, 16777215)
        
        self.stack_root = self.settings.get("stack_root", "")

        central = QWidget()
        central.setObjectName("CentralRoot")
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(200)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(4)
        
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(16, 10, 16, 15)
        brand_row.setSpacing(10)
        
        brand_title = QLabel("DevStack")
        brand_title.setObjectName("BrandTitle")
        brand_row.addWidget(brand_title, 1)
        
        self.status_dot = QLabel()
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setProperty("status", "stopped")
        brand_row.addWidget(self.status_dot, 0, Qt.AlignVCenter)
        
        sidebar_layout.addLayout(brand_row)
        
        sep = QFrame()
        sep.setObjectName("SidebarSeparator")
        sep.setFixedHeight(1)
        sidebar_layout.addWidget(sep)
        sidebar_layout.addSpacing(8)
        
        self.nav_buttons = []
        nav_data = [
            ("Control",  "", 0),
            ("Websites", "", 1),
            ("Services", "", 2),
            ("Logs",     "", 3),
            ("Settings", "", 4),
        ]
        
        for title, glyph, idx in nav_data:
            btn = SidebarButton(title, glyph, idx, self)
            btn.clicked.connect(lambda i=idx: self._on_nav_clicked(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            
        sidebar_layout.addStretch(1)
        
        # Theme Switcher Button
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("ThemeToggleBtn")
        current_theme = self.settings.get("theme", "light")
        self.theme_btn.setText("🌙 Dark Mode" if current_theme == "light" else "☀️ Light Mode")
        self.theme_btn.clicked.connect(self._toggle_theme)
        
        theme_row = QHBoxLayout()
        theme_row.setContentsMargins(16, 0, 16, 12)
        theme_row.addWidget(self.theme_btn)
        sidebar_layout.addLayout(theme_row)
        
        # Clickable Developer Credit Footer
        footer_layout = QVBoxLayout()
        footer_layout.setContentsMargins(20, 0, 20, 14)
        footer_layout.setSpacing(4)

        self.sidebar_footer = QLabel("System Status")
        self.sidebar_footer.setObjectName("SidebarFooter")
        footer_layout.addWidget(self.sidebar_footer)

        self.credit_label = QLabel('By <a href="https://vjranga.com" style="color: #E55B3C; text-decoration: none; font-weight: bold;">vjranga.com</a>')
        self.credit_label.setObjectName("SidebarCredit")
        self.credit_label.setOpenExternalLinks(True)
        footer_layout.addWidget(self.credit_label)

        sidebar_layout.addLayout(footer_layout)
        
        main_layout.addWidget(self.sidebar)
        
        self.pages = QStackedWidget()
        self.pages.setObjectName("MainPages")
        
        self.overview_tab = OverviewTab(self)
        self.websites_tab = WebsitesTab(self)
        self.services_tab = ServicesTab(self)
        self.logs_tab = LogsTab(self)
        self.settings_tab = SettingsTab(self)
        
        self.pages.addWidget(self.overview_tab)
        self.pages.addWidget(self.websites_tab)
        self.pages.addWidget(self.services_tab)
        self.pages.addWidget(self.logs_tab)
        self.pages.addWidget(self.settings_tab)
        
        main_layout.addWidget(self.pages)

        self._setup_menubar()
        self._update_sidebar_active_state(0)
        self._apply_ui_density(self.settings.get("ui_density", "comfortable"))

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._refresh_all)
        self.status_timer.start(self.settings.get("auto_refresh_interval", 5) * 1000)
        self._refresh_all()

    def _setup_menubar(self):
        menubar = self.menuBar()

        customize_action = QAction("UI Customize", self)
        customize_action.triggered.connect(self._show_customize_dialog)
        menubar.addAction(customize_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        menubar.addAction(about_action)


    def _show_customize_dialog(self):
        dialog = CustomizeUIDialog(self)
        dialog.exec()

    def _show_about(self):
        QMessageBox.about(
            self,
            "About DevStack Manager",
            "DevStack Manager v1.0\n\nDeveloped by VJ-Ranga (vjranga.com)\nIT Specialist & Digital Operations Consultant.\n\nA standalone desktop application for managing\nyour portable web development stack.",
        )

    def _refresh_all(self):
        if self._closing:
            return
        if self._refresh_worker and self._refresh_worker.isRunning():
            self._pending_refresh = True
            return
        # Safe to drop old worker here — isRunning() returned False so C++ is fully done
        self._refresh_worker = None
        self._pending_refresh = False
        worker = RefreshWorker(self.get_stack_root())
        worker.finished.connect(self._on_refresh_done)
        self._refresh_worker = worker
        worker.start()

    def _on_refresh_done(self, status: dict, versions: dict):
        # Do NOT null _refresh_worker here — C++ d->running may still be True
        # when the finished signal fires; GC here causes the "Destroyed while running" crash.
        # The reference is safely cleared at the top of _refresh_all() instead.
        self.overview_tab.apply_refresh(status, versions)
        self.services_tab.apply_status(status)
        
        overall = status.get("overall", "stopped")
        self.status_dot.setProperty("status", overall)
        repolish(self.status_dot)
        
        machine = status.get("machine", "")
        if machine:
            self.sidebar_footer.setText(f"System: {machine}")
            
        if self._pending_refresh:
            self._refresh_all()

    def notify_service_state_changed(self):
        self._refresh_all()
        # Delayed second refresh so UI catches service state after process settles.
        # _refresh_all guards against _closing so the timer is safe across shutdown.
        QTimer.singleShot(1200, self._refresh_all)

    def _on_nav_clicked(self, index):
        self.pages.setCurrentIndex(index)
        self._on_tab_changed(index)
        self._update_sidebar_active_state(index)

    def _update_sidebar_active_state(self, active_index):
        for btn in self.nav_buttons:
            is_active = (btn.index == active_index)
            btn.set_active(is_active)

    def _on_tab_changed(self, index):
        if index in (self.pages.indexOf(self.overview_tab), self.pages.indexOf(self.services_tab)):
            self._refresh_all()
        elif index == self.pages.indexOf(self.websites_tab):
            self.websites_tab.refresh_sites()
        elif index == self.pages.indexOf(self.logs_tab):
            self.logs_tab.load_current()

    def get_stack_root(self) -> str:
        return self.stack_root

    def get_open_urls(self) -> dict:
        nginx_port = int(self.settings.get("nginx_port", 80))
        frontend = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"
        return {
            "nginx": frontend + "/",
            "phpmyadmin": frontend + "/phpmyadmin/",
            "dashboard": frontend + "/dashboard/",
        }

    def open_target(self, target: str):
        url = self.get_open_urls().get(target)
        if url:
            webbrowser.open(url)

    def set_stack_root(self, path: str):
        from pathlib import Path

        self.stack_root = str(Path(path).resolve())
        self._refresh_all()

    def apply_settings(self, settings: dict):
        self.settings.update(settings)
        self.status_timer.start(self.settings.get("auto_refresh_interval", 5) * 1000)
        self._apply_ui_density(self.settings.get("ui_density", "comfortable"))

    def _apply_ui_density(self, density: str):
        theme = self.settings.get("theme", "light")
        self.setStyleSheet(build_stylesheet(density, theme))
        for tab in (self.overview_tab, self.websites_tab, self.services_tab, self.logs_tab, self.settings_tab):
            if hasattr(tab, "apply_density"):
                tab.apply_density(density)

    def _toggle_theme(self):
        current = self.settings.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self.settings["theme"] = new_theme
        
        from core.config import save_settings
        save_settings(self.settings)
        
        self._apply_ui_density(self.settings.get("ui_density", "comfortable"))
        self.theme_btn.setText("🌙 Dark Mode" if new_theme == "light" else "☀️ Light Mode")

    def closeEvent(self, event):
        self._closing = True
        self.status_timer.stop()
        # Collect every known worker across all tabs
        workers = [
            self._refresh_worker,
            getattr(self.overview_tab,  "_service_worker",   None),
            getattr(self.services_tab,  "_action_worker",    None),
            getattr(self.settings_tab,  "_switch_worker",    None),
            getattr(self.settings_tab,  "_ext_apply_worker", None),
            getattr(self.settings_tab,  "dl_worker",         None),
            getattr(self.settings_tab,  "_mcp_worker",       None),
        ]
        for worker in workers:
            if worker and worker.isRunning():
                worker.wait(5000)
        event.accept()
