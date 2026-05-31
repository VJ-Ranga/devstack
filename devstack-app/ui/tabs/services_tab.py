from PySide6.QtCore import QThread, Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from core.service_manager import restart, start, stop
from ui.styles import FLUENT_GLYPHS, density_button_height, repolish, set_status_badge, set_status_frame

_SERVICE_GLYPHS = {
    "nginx":  FLUENT_GLYPHS["nginx"],
    "php":    FLUENT_GLYPHS["php"],
    "mysql":  FLUENT_GLYPHS["phpmyadmin"],
}


class ServiceActionWorker(QThread):
    finished = Signal(str, dict)

    def __init__(self, stack_root, action, service):
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
        self.finished.emit(self.service, result)


class ServicesTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._action_worker = None
        self._service_widgets = {}

        # Busy-animation state for the active service's badge
        self._busy_timer = QTimer(self)
        self._busy_timer.setInterval(350)
        self._busy_timer.timeout.connect(self._tick_busy)
        self._busy_phase = 0
        self._busy_badge = None
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
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        title = QLabel("Services")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Start, stop, and restart individual services in your stack.")
        subtitle.setObjectName("BodyText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(6)

        section_lbl = QLabel("SERVICE LIST")
        section_lbl.setObjectName("SectionLabel")
        layout.addWidget(section_lbl)

        rows_layout = QVBoxLayout()
        rows_layout.setSpacing(6)

        for key, name, port, desc, open_target in (
            ("nginx",  "Nginx Web Server", 80,   "Main web entry point",  "nginx"),
            ("php",    "PHP FastCGI",      9000, "PHP runtime (FastCGI)", None),
            ("mysql",  "MariaDB Database", 3306, "Database server",       "phpmyadmin"),
        ):
            row = QFrame()
            row.setObjectName("ServiceRow")
            set_status_frame(row, "stopped")
            row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            # Single horizontal row
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 10, 14, 10)
            row_layout.setSpacing(12)

            # Status icon box
            icon_box = QFrame()
            icon_box.setObjectName("StatusIconBox")
            set_status_frame(icon_box, "stopped")
            icon_box.setFixedSize(32, 32)
            ib = QVBoxLayout(icon_box)
            ib.setContentsMargins(0, 0, 0, 0)
            ib.setAlignment(Qt.AlignCenter)
            icon_lbl = QLabel(_SERVICE_GLYPHS[key])
            icon_lbl.setObjectName("StatusIconGlyph")
            set_status_badge(icon_lbl, "stopped")
            icon_lbl.setAlignment(Qt.AlignCenter)
            ib.addWidget(icon_lbl)
            row_layout.addWidget(icon_box, 0, Qt.AlignVCenter)

            # Name + meta (takes all spare space)
            info_col = QVBoxLayout()
            info_col.setSpacing(2)
            name_lbl = QLabel(name)
            name_lbl.setObjectName("RowTitle")
            meta_lbl = QLabel(f"Port {port}  •  {desc}")
            meta_lbl.setObjectName("RowMeta")
            info_col.addWidget(name_lbl)
            info_col.addWidget(meta_lbl)
            row_layout.addLayout(info_col, 1)

            # Status badge
            badge = QLabel("Stopped")
            badge.setObjectName("StatusBadge")
            set_status_badge(badge, "stopped")
            row_layout.addWidget(badge, 0, Qt.AlignVCenter)

            # Action buttons — no fixed width so text never clips
            row_layout.addSpacing(4)

            action_btn = QPushButton("Start")
            action_btn.setObjectName("PrimaryButton")
            action_btn.clicked.connect(lambda checked=False, k=key: self._on_action_btn_clicked(k))
            row_layout.addWidget(action_btn, 0, Qt.AlignVCenter)

            restart_btn = QPushButton("Restart")
            restart_btn.setObjectName("DefaultButton")
            restart_btn.clicked.connect(lambda checked=False, k=key: self._run_action(k, "restart"))
            row_layout.addWidget(restart_btn, 0, Qt.AlignVCenter)

            open_btn = None
            if open_target:
                open_btn = QPushButton("Open")
                open_btn.setObjectName("DefaultButton")
                open_btn.clicked.connect(lambda checked=False, t=open_target: self.main_window.open_target(t))
                row_layout.addWidget(open_btn, 0, Qt.AlignVCenter)

            rows_layout.addWidget(row)
            self._service_widgets[key] = {
                "row":        row,
                "icon_box":   icon_box,
                "icon":       icon_lbl,
                "badge":      badge,
                "action_btn": action_btn,
                "restart_btn": restart_btn,
                "open_btn":   open_btn,
            }

        layout.addLayout(rows_layout)
        layout.addStretch()
        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    # ── button-state helpers ────────────────────────────────────────────

    def _on_action_btn_clicked(self, service):
        state = self._service_widgets[service]["badge"].text().lower()
        if "running" in state or "starting" in state:
            self._run_action(service, "stop")
        else:
            self._run_action(service, "start")

    def _run_action(self, service, action):
        if self._action_worker and self._action_worker.isRunning():
            return
        for data in self._service_widgets.values():
            data["action_btn"].setEnabled(False)
            data["restart_btn"].setEnabled(False)
            if data.get("open_btn"):
                data["open_btn"].setEnabled(False)
        current = self._service_widgets.get(service)
        if current:
            verb = "Starting" if action == "start" else "Stopping" if action == "stop" else "Restarting"
            set_status_badge(current["badge"], "partial")
            self._start_busy(current["badge"], verb)
        # Drop previous finished worker before creating a new one (safe: isRunning() == False)
        self._action_worker = None
        worker = ServiceActionWorker(self.main_window.get_stack_root(), action, service)
        worker.finished.connect(self._on_action_done)
        self._action_worker = worker
        worker.start()

    def _start_busy(self, badge, verb: str):
        self._busy_badge = badge
        self._busy_verb = verb
        self._busy_phase = 0
        self._busy_timer.start()
        self._tick_busy()

    def _tick_busy(self):
        if self._busy_badge:
            self._busy_badge.setText(self._busy_verb + "." * (self._busy_phase % 4))
        self._busy_phase += 1

    def _stop_busy(self):
        self._busy_timer.stop()
        self._busy_badge = None

    def _on_action_done(self, service, result):
        # Do NOT null _action_worker here — C++ d->running may still be True at signal time
        self._stop_busy()
        for data in self._service_widgets.values():
            data["action_btn"].setEnabled(True)
            data["restart_btn"].setEnabled(True)
            if data.get("open_btn"):
                data["open_btn"].setEnabled(True)
        if not result.get("success"):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Service Action Failed", result.get("error", "Unknown error"))
        self.main_window.notify_service_state_changed()

    # ── status update from main refresh ───────────────────────────────

    def apply_status(self, status: dict):
        glyph_state = {
            "running": FLUENT_GLYPHS["running"],
            "partial": FLUENT_GLYPHS["partial"],
            "stopped": FLUENT_GLYPHS["stopped"],
        }
        for svc in status.get("services", []):
            key = svc.get("key")
            if key not in self._service_widgets:
                continue
            state = svc.get("state", "stopped")
            label = "Needs Attention" if state == "partial" else state.title()
            data = self._service_widgets[key]
            data["badge"].setText(label)
            data["badge"].setToolTip(
                "Process is running but the port is not yet listening.\n"
                "This may resolve in a few seconds, or indicate a config error.\n"
                "Check the Logs tab for details."
                if state == "partial" else ""
            )
            data["icon"].setText(glyph_state[state])
            set_status_frame(data["row"],      state)
            set_status_frame(data["icon_box"], state)
            set_status_badge(data["badge"],    state)
            set_status_badge(data["icon"],     state)

            is_running = (state == "running")
            is_partial = (state == "partial")

            action_btn = data.get("action_btn")
            if action_btn:
                if is_running:
                    action_btn.setText("Stop")
                    action_btn.setObjectName("DangerButton")
                else:
                    action_btn.setText("Start")
                    action_btn.setObjectName("PrimaryButton")
                repolish(action_btn)
                action_btn.setEnabled(True)

            if data.get("restart_btn"):
                data["restart_btn"].setEnabled(is_running or is_partial)
            if data.get("open_btn"):
                data["open_btn"].setEnabled(is_running)

    def apply_density(self, density: str):
        h = density_button_height(density)
        for data in self._service_widgets.values():
            for k in ("action_btn", "restart_btn", "open_btn"):
                btn = data.get(k)
                if btn:
                    btn.setFixedHeight(h)
                    repolish(btn)
