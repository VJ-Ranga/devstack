from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from core.service_manager import restart, start, stop
from ui.styles import FLUENT_GLYPHS, density_button_height, repolish, set_status_badge, set_status_frame
from ui.widgets import QuickAccessCard


class ServiceWorker(QThread):
    finished = Signal(dict)

    def __init__(self, stack_root, action, service="all"):
        super().__init__()
        self.stack_root = stack_root
        self.action = action
        self.service = service

    def run(self):
        if self.action == "start":
            result = start(self.stack_root, self.service)
        elif self.action == "stop":
            result = stop(self.stack_root, self.service)
        else:
            result = restart(self.stack_root, self.service)
        self.finished.emit(result)


class OverviewTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._service_worker = None
        self.quick_open_cards = []
        self.service_rows = {}
        self.version_labels = {}
        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("TabPage")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("Control Center")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        intro = QLabel("Control the stack, check service status, and open the main tools from one place.")
        intro.setObjectName("BodyText")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        status_section = QFrame()
        status_section.setObjectName("Panel")
        status_layout = QVBoxLayout(status_section)
        status_layout.setContentsMargins(20, 18, 20, 18)
        status_layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        title_block = QVBoxLayout()
        title_block.setSpacing(4)
        self.health_label = QLabel("Checking services")
        self.health_label.setObjectName("SummaryTitle")
        self.health_detail = QLabel("Waiting for the latest status from the local stack.")
        self.health_detail.setObjectName("BodyText")
        self.health_detail.setWordWrap(True)
        title_block.addWidget(self.health_label)
        title_block.addWidget(self.health_detail)
        top_row.addLayout(title_block, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.start_btn = QPushButton("Start All")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(lambda: self._run_action("start"))
        actions.addWidget(self.start_btn)
        self.stop_btn = QPushButton("Stop All")
        self.stop_btn.setObjectName("DangerButton")
        self.stop_btn.clicked.connect(lambda: self._run_action("stop"))
        actions.addWidget(self.stop_btn)
        self.restart_btn = QPushButton("Restart All")
        self.restart_btn.setObjectName("DefaultButton")
        self.restart_btn.clicked.connect(lambda: self._run_action("restart"))
        actions.addWidget(self.restart_btn)
        top_row.addLayout(actions)
        status_layout.addLayout(top_row)

        self.summary_line = QLabel("Running 0 of 4 services")
        self.summary_line.setObjectName("MetaText")
        status_layout.addWidget(self.summary_line)
        layout.addWidget(status_section)

        quick_label = QLabel("QUICK ACCESS")
        quick_label.setObjectName("SectionLabel")
        layout.addWidget(quick_label)

        quick_grid = QGridLayout()
        quick_grid.setHorizontalSpacing(8)
        quick_grid.setVerticalSpacing(8)
        quick_data = (
            ("Open Nginx", "Port 80", "nginx", "nginx"),
            ("Open Apache", "Port 8088", "apache", "apache"),
            ("Open phpMyAdmin", "Database admin", "phpmyadmin", "phpmyadmin"),
            ("Open Web Interface", "Dashboard", "dashboard", "dashboard"),
        )
        for i, (title_text, subtitle_text, glyph, target) in enumerate(quick_data):
            card = QuickAccessCard(title_text, subtitle_text, glyph)
            card.clicked.connect(lambda t=target: self.main_window.open_target(t))
            quick_grid.addWidget(card, i // 2, i % 2)
            self.quick_open_cards.append(card)
        layout.addLayout(quick_grid)

        services_label = QLabel("SERVICE STATUS")
        services_label.setObjectName("SectionLabel")
        layout.addWidget(services_label)

        service_list = QVBoxLayout()
        service_list.setSpacing(8)
        for name, key, port, description in (
            ("Apache", "apache", 8088, "Backend web server"),
            ("Nginx", "nginx", 80, "Main web entry point"),
            ("PHP FastCGI", "php", 9000, "PHP runtime"),
            ("MariaDB", "mysql", 3306, "Database server"),
        ):
            row = QFrame()
            row.setObjectName("ServiceRow")
            set_status_frame(row, "stopped")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 14, 16, 14)
            row_layout.setSpacing(12)

            icon_box = QFrame()
            icon_box.setObjectName("StatusIconBox")
            set_status_frame(icon_box, "stopped")
            icon_layout = QVBoxLayout(icon_box)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_layout.setAlignment(Qt.AlignCenter)
            icon = QLabel(FLUENT_GLYPHS["stopped"])
            icon.setObjectName("StatusIconGlyph")
            set_status_badge(icon, "stopped")
            icon_layout.addWidget(icon)
            row_layout.addWidget(icon_box)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            title_label = QLabel(name)
            title_label.setObjectName("RowTitle")
            desc_label = QLabel(description)
            desc_label.setObjectName("BodyText")
            meta = QLabel(f"Port {port}")
            meta.setObjectName("MetaText")
            text_col.addWidget(title_label)
            text_col.addWidget(desc_label)
            text_col.addWidget(meta)
            row_layout.addLayout(text_col, 1)

            badge = QLabel("Stopped")
            badge.setObjectName("StatusBadge")
            set_status_badge(badge, "stopped")
            row_layout.addWidget(badge, 0, Qt.AlignVCenter)
            service_list.addWidget(row)
            self.service_rows[key] = {"row": row, "icon_box": icon_box, "icon": icon, "badge": badge}
        layout.addLayout(service_list)

        versions_label = QLabel("VERSIONS")
        versions_label.setObjectName("SectionLabel")
        layout.addWidget(versions_label)

        versions_panel = QFrame()
        versions_panel.setObjectName("Panel")
        versions_layout = QGridLayout(versions_panel)
        versions_layout.setContentsMargins(20, 18, 20, 18)
        versions_layout.setHorizontalSpacing(12)
        versions_layout.setVerticalSpacing(8)
        for row_index, (key, text) in enumerate((("apache", "Apache"), ("nginx", "Nginx"), ("php", "PHP"), ("mysql", "MariaDB"))):
            label = QLabel(text)
            label.setObjectName("RowTitle")
            value = QLabel("Not checked")
            value.setObjectName("ValueText")
            versions_layout.addWidget(label, row_index, 0)
            versions_layout.addWidget(value, row_index, 1)
            self.version_labels[key] = value
        layout.addWidget(versions_panel)

        layout.addStretch()
        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def _run_action(self, action):
        if self._service_worker and self._service_worker.isRunning():
            return
        state_text = {
            "start": ("Starting services", "Bringing the local stack online."),
            "stop": ("Stopping services", "Shutting down all core services."),
            "restart": ("Restarting services", "Refreshing the local stack."),
        }
        title, detail = state_text[action]
        self.health_label.setText(title)
        self.health_detail.setText(detail)
        for btn in (self.start_btn, self.stop_btn, self.restart_btn):
            btn.setEnabled(False)
        worker = ServiceWorker(self.main_window.get_stack_root(), action)
        worker.finished.connect(self._on_action_done)
        worker.finished.connect(worker.deleteLater)
        self._service_worker = worker
        worker.start()

    def _on_action_done(self, result):
        self._service_worker = None
        for btn in (self.start_btn, self.stop_btn, self.restart_btn):
            btn.setEnabled(True)
        if not result.get("success"):
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Service Action Failed", result.get("error", "Unknown error"))
        self.main_window.notify_service_state_changed()

    def apply_refresh(self, status: dict, versions: dict):
        running = 0
        partial = 0
        total = len(status.get("services", []))
        overall = status.get("overall", "stopped")
        if overall == "running":
            self.health_label.setText("All services running")
            self.health_detail.setText("The stack is ready to use.")
        elif overall == "partial":
            self.health_label.setText("Some services need attention")
            self.health_detail.setText("One or more services is only partially available.")
        else:
            self.health_label.setText("All services stopped")
            self.health_detail.setText("Start the stack to use Apache, Nginx, PHP, and MariaDB.")

        glyph_map = {"running": FLUENT_GLYPHS["running"], "partial": FLUENT_GLYPHS["partial"], "stopped": FLUENT_GLYPHS["stopped"]}
        for svc in status.get("services", []):
            key = svc.get("key")
            state = svc.get("state", "stopped")
            if state == "running":
                running += 1
            elif state == "partial":
                partial += 1
            if key in self.service_rows:
                parts = self.service_rows[key]
                parts["badge"].setText("Needs Attention" if state == "partial" else state.title())
                parts["icon"].setText(glyph_map[state])
                set_status_frame(parts["row"], state)
                set_status_frame(parts["icon_box"], state)
                set_status_badge(parts["badge"], state)
                set_status_badge(parts["icon"], state)

        stopped = max(0, total - running - partial)
        self.summary_line.setText(f"Running {running} of {total} services. Partial: {partial}. Stopped: {stopped}.")
        for key, value in self.version_labels.items():
            value.setText(versions.get(key) or "Not found")

    def apply_density(self, density: str):
        h = density_button_height(density)
        for btn in [self.start_btn, self.stop_btn, self.restart_btn]:
            btn.setFixedHeight(h)
            repolish(btn)
