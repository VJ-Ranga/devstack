import webbrowser

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMessageBox, QTabWidget, QVBoxLayout, QWidget

from core.config import load_settings
from core.status_reader import get_status
from core.version_reader import get_all_versions
from ui.styles import build_stylesheet
from ui.tabs.logs_tab import LogsTab
from ui.tabs.overview_tab import OverviewTab
from ui.tabs.services_tab import ServicesTab
from ui.tabs.settings_tab import SettingsTab


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
        self.setWindowTitle("DevStack Manager")
        self.resize(960, 680)
        self.setMinimumSize(720, 520)
        self.stack_root = self.settings.get("stack_root", "")

        central = QWidget()
        central.setObjectName("CentralRoot")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.overview_tab = OverviewTab(self)
        self.services_tab = ServicesTab(self)
        self.logs_tab = LogsTab(self)
        self.settings_tab = SettingsTab(self)

        self.tabs.addTab(self.overview_tab, "Control")
        self.tabs.addTab(self.services_tab, "Services")
        self.tabs.addTab(self.logs_tab, "Logs")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        self._setup_menubar()
        self._apply_ui_density(self.settings.get("ui_density", "comfortable"))

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._refresh_all)
        self.status_timer.start(self.settings.get("auto_refresh_interval", 5) * 1000)
        self._refresh_all()

    def _setup_menubar(self):
        file_menu = self.menuBar().addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self):
        QMessageBox.about(
            self,
            "About DevStack Manager",
            "DevStack Manager v1.0\n\nA standalone desktop application for managing\nyour portable web development stack.\n\nBuilt with Python and PySide6.",
        )

    def _refresh_all(self):
        if self._refresh_worker and self._refresh_worker.isRunning():
            self._pending_refresh = True
            return
        self._pending_refresh = False
        worker = RefreshWorker(self.get_stack_root())
        worker.finished.connect(self._on_refresh_done)
        worker.finished.connect(worker.deleteLater)
        self._refresh_worker = worker
        worker.start()

    def _on_refresh_done(self, status: dict, versions: dict):
        self._refresh_worker = None
        self.overview_tab.apply_refresh(status, versions)
        self.services_tab.apply_status(status)
        if self._pending_refresh:
            self._refresh_all()

    def notify_service_state_changed(self):
        self._refresh_all()
        QTimer.singleShot(1200, self._refresh_all)

    def _on_tab_changed(self, index):
        if index in (self.tabs.indexOf(self.overview_tab), self.tabs.indexOf(self.services_tab)):
            self._refresh_all()

    def get_stack_root(self) -> str:
        return self.stack_root

    def get_open_urls(self) -> dict:
        nginx_port = int(self.settings.get("nginx_port", 80))
        apache_port = int(self.settings.get("apache_port", 8088))
        frontend = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"
        apache = f"http://localhost:{apache_port}"
        return {
            "nginx": frontend + "/",
            "apache": apache + "/",
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
        self.setStyleSheet(build_stylesheet(density))
        for tab in (self.overview_tab, self.services_tab, self.logs_tab, self.settings_tab):
            if hasattr(tab, "apply_density"):
                tab.apply_density(density)

    def closeEvent(self, event):
        self.status_timer.stop()
        event.accept()
