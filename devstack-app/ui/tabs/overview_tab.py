from PySide6.QtCore import QThread, Qt, Signal, QTimer
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget

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

        # Busy-animation state (loading feedback while a start/stop/restart runs)
        self._busy_timer = QTimer(self)
        self._busy_timer.setInterval(350)
        self._busy_timer.timeout.connect(self._tick_busy)
        self._busy_phase = 0
        self._busy_label_base = ""
        self._busy_btn = None
        self._busy_btn_base = ""
        self._busy_verb = ""

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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

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
        status_layout.setContentsMargins(16, 12, 16, 12)
        status_layout.setSpacing(12)

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

        self.summary_line = QLabel("Running 0 of 3 services")
        self.summary_line.setObjectName("MetaText")
        status_layout.addWidget(self.summary_line)

        # Indeterminate progress bar — shown only while an action runs
        self.busy_bar = QProgressBar()
        self.busy_bar.setRange(0, 0)  # indeterminate (animated sweep)
        self.busy_bar.setTextVisible(False)
        self.busy_bar.setFixedHeight(4)
        self.busy_bar.hide()
        status_layout.addWidget(self.busy_bar)

        layout.addWidget(status_section)

        quick_label = QLabel("QUICK ACCESS")
        quick_label.setObjectName("SectionLabel")
        layout.addWidget(quick_label)

        quick_grid = QGridLayout()
        quick_grid.setHorizontalSpacing(8)
        quick_grid.setVerticalSpacing(8)
        quick_data = (
            ("Open Site", "Local portal", "nginx", "nginx"),
            ("phpMyAdmin", "Database admin", "phpmyadmin", "phpmyadmin"),
            ("Dashboard", "Status monitor", "dashboard", "dashboard"),
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

        service_grid = QGridLayout()
        service_grid.setHorizontalSpacing(8)
        service_grid.setVerticalSpacing(8)

        services_data = (
            ("Nginx", "nginx", 80, "Web server"),
            ("PHP FastCGI", "php", 9000, "PHP runtime"),
            ("MariaDB", "mysql", 3306, "Database server"),
        )

        for i, (name, key, port, description) in enumerate(services_data):
            card = QFrame()
            card.setObjectName("ServiceRow")
            set_status_frame(card, "stopped")

            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(10)

            icon_box = QFrame()
            icon_box.setObjectName("StatusIconBox")
            set_status_frame(icon_box, "stopped")
            icon_box.setFixedSize(32, 32)

            icon_layout = QVBoxLayout(icon_box)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_layout.setAlignment(Qt.AlignCenter)
            icon = QLabel(FLUENT_GLYPHS["stopped"])
            icon.setObjectName("StatusIconGlyph")
            set_status_badge(icon, "stopped")
            icon_layout.addWidget(icon)
            card_layout.addWidget(icon_box)

            text_block = QVBoxLayout()
            text_block.setSpacing(2)
            title_label = QLabel(name)
            title_label.setObjectName("RowTitle")
            meta_label = QLabel(f"Port {port}")
            meta_label.setObjectName("MetaText")
            text_block.addWidget(title_label)
            text_block.addWidget(meta_label)
            card_layout.addLayout(text_block, 1)

            badge = QLabel("Stopped")
            badge.setObjectName("StatusBadge")
            set_status_badge(badge, "stopped")
            card_layout.addWidget(badge, 0, Qt.AlignVCenter)

            service_grid.addWidget(card, i // 2, i % 2)
            self.service_rows[key] = {"row": card, "icon_box": icon_box, "icon": icon, "badge": badge}

        layout.addLayout(service_grid)

        versions_label = QLabel("VERSIONS")
        versions_label.setObjectName("SectionLabel")
        layout.addWidget(versions_label)

        versions_panel = QFrame()
        versions_panel.setObjectName("Panel")
        versions_layout = QGridLayout(versions_panel)
        versions_layout.setContentsMargins(16, 12, 16, 12)
        versions_layout.setHorizontalSpacing(12)
        versions_layout.setVerticalSpacing(6)
        for row_index, (key, text) in enumerate((("nginx", "Nginx"), ("php", "PHP"), ("mysql", "MariaDB"))):
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
            "start": ("Starting services", "Bringing the local stack online.", self.start_btn),
            "stop": ("Stopping services", "Shutting down all core services.", self.stop_btn),
            "restart": ("Restarting services", "Refreshing the local stack.", self.restart_btn),
        }
        title, detail, btn = state_text[action]
        self.health_detail.setText(detail)
        for b in (self.start_btn, self.stop_btn, self.restart_btn):
            b.setEnabled(False)

        # Start the loading animation (progress bar + pulsing dots + button spinner)
        self._start_busy(title, btn, {"start": "Starting", "stop": "Stopping", "restart": "Restarting"}[action])

        # Drop previous finished worker safely before creating a new one
        self._service_worker = None
        worker = ServiceWorker(self.main_window.get_stack_root(), action)
        worker.finished.connect(self._on_action_done)
        self._service_worker = worker
        worker.start()

    def _on_action_done(self, result):
        # Do NOT null _service_worker here — see RefreshWorker note in main_window.py
        self._stop_busy()
        for btn in (self.start_btn, self.stop_btn, self.restart_btn):
            btn.setEnabled(True)
        if not result.get("success"):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Service Action Failed", result.get("error", "Unknown error"))
        self.main_window.notify_service_state_changed()

    # ── Loading animation ───────────────────────────────────────────────────

    def _start_busy(self, label_base: str, btn, verb: str):
        self._busy_label_base = label_base
        self._busy_btn = btn
        self._busy_btn_base = btn.text() if btn else ""
        self._busy_verb = verb
        self._busy_phase = 0
        self.busy_bar.show()
        self._busy_timer.start()
        self._tick_busy()

    def _tick_busy(self):
        dots = "." * (self._busy_phase % 4)
        self.health_label.setText(self._busy_label_base + dots)
        if self._busy_btn:
            self._busy_btn.setText(self._busy_verb + dots)
        self._busy_phase += 1

    def _stop_busy(self):
        self._busy_timer.stop()
        self.busy_bar.hide()
        if self._busy_btn:
            self._busy_btn.setText(self._busy_btn_base)
            self._busy_btn = None

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
            self.health_detail.setText("Start the stack to use Nginx, PHP, and MariaDB.")

        if overall == "running":
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif overall == "stopped":
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        else:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)

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
                parts["badge"].setToolTip(
                    "Process is running but the port is not yet listening.\n"
                    "This may resolve in a few seconds, or indicate a config error.\n"
                    "Check the Logs tab for details."
                    if state == "partial" else ""
                )
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
