from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from core.service_manager import restart, start, stop
from ui.styles import FLUENT_GLYPHS, density_button_height, repolish, set_status_badge, set_status_frame


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

        title = QLabel("Services")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Use this page when you want direct control of each service.")
        subtitle.setObjectName("BodyText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        services_label = QLabel("SERVICE LIST")
        services_label.setObjectName("SectionLabel")
        layout.addWidget(services_label)

        rows_layout = QVBoxLayout()
        rows_layout.setSpacing(8)
        glyph_map = {"apache": FLUENT_GLYPHS["apache"], "nginx": FLUENT_GLYPHS["nginx"], "php": FLUENT_GLYPHS["partial"], "mysql": FLUENT_GLYPHS["phpmyadmin"]}
        for key, name, exe, port, desc, open_target in (
            ("apache", "Apache HTTP Server", "apache\\bin\\httpd.exe", 8088, "Backend web server", "apache"),
            ("nginx", "Nginx Web Server", "nginx\\nginx.exe", 80, "Main web entry point", "nginx"),
            ("php", "PHP FastCGI", "php\\php-cgi.exe", 9000, "PHP runtime", None),
            ("mysql", "MariaDB Database", "mysql\\bin\\mysqld.exe", 3306, "Database server", "phpmyadmin"),
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
            icon = QLabel(glyph_map[key])
            icon.setObjectName("StatusIconGlyph")
            set_status_badge(icon, "stopped")
            icon_layout.addWidget(icon)
            row_layout.addWidget(icon_box)

            left = QVBoxLayout()
            left.setSpacing(2)
            row_title = QLabel(name)
            row_title.setObjectName("RowTitle")
            row_desc = QLabel(desc)
            row_desc.setObjectName("BodyText")
            row_meta = QLabel(f"Port {port}    {exe}")
            row_meta.setObjectName("MetaText")
            left.addWidget(row_title)
            left.addWidget(row_desc)
            left.addWidget(row_meta)
            row_layout.addLayout(left, 1)

            badge = QLabel("Stopped")
            badge.setObjectName("StatusBadge")
            set_status_badge(badge, "stopped")
            row_layout.addWidget(badge, 0, Qt.AlignVCenter)

            actions = QHBoxLayout()
            actions.setSpacing(8)
            start_btn = QPushButton("Start")
            start_btn.setObjectName("PrimaryButton")
            start_btn.clicked.connect(lambda checked=False, k=key: self._run_action(k, "start"))
            actions.addWidget(start_btn)
            stop_btn = QPushButton("Stop")
            stop_btn.setObjectName("DangerButton")
            stop_btn.clicked.connect(lambda checked=False, k=key: self._run_action(k, "stop"))
            actions.addWidget(stop_btn)
            restart_btn = QPushButton("Restart")
            restart_btn.setObjectName("DefaultButton")
            restart_btn.clicked.connect(lambda checked=False, k=key: self._run_action(k, "restart"))
            actions.addWidget(restart_btn)
            open_btn = None
            if open_target:
                open_btn = QPushButton("Open")
                open_btn.setObjectName("DefaultButton")
                open_btn.clicked.connect(lambda checked=False, t=open_target: self.main_window.open_target(t))
                actions.addWidget(open_btn)
            row_layout.addLayout(actions)

            rows_layout.addWidget(row)
            self._service_widgets[key] = {"row": row, "icon_box": icon_box, "icon": icon, "badge": badge, "start_btn": start_btn, "stop_btn": stop_btn, "restart_btn": restart_btn, "open_btn": open_btn}

        layout.addLayout(rows_layout)
        layout.addStretch()
        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def _run_action(self, service, action):
        if self._action_worker and self._action_worker.isRunning():
            return
        for data in self._service_widgets.values():
            data["start_btn"].setEnabled(False)
            data["stop_btn"].setEnabled(False)
            data["restart_btn"].setEnabled(False)
        current = self._service_widgets.get(service)
        if current:
            current["badge"].setText("Starting" if action == "start" else "Stopping" if action == "stop" else "Restarting")
            set_status_badge(current["badge"], "partial")
        worker = ServiceActionWorker(self.main_window.get_stack_root(), action, service)
        worker.finished.connect(self._on_action_done)
        worker.finished.connect(worker.deleteLater)
        self._action_worker = worker
        worker.start()

    def _on_action_done(self, service, result):
        self._action_worker = None
        for data in self._service_widgets.values():
            data["start_btn"].setEnabled(True)
            data["stop_btn"].setEnabled(True)
            data["restart_btn"].setEnabled(True)
        if not result.get("success"):
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Service Action Failed", result.get("error", "Unknown error"))
        self.main_window.notify_service_state_changed()

    def apply_status(self, status: dict):
        glyph_state_map = {"running": FLUENT_GLYPHS["running"], "partial": FLUENT_GLYPHS["partial"], "stopped": FLUENT_GLYPHS["stopped"]}
        for svc in status.get("services", []):
            key = svc.get("key")
            if key not in self._service_widgets:
                continue
            state = svc.get("state", "stopped")
            label = "Needs Attention" if state == "partial" else state.title()
            data = self._service_widgets[key]
            data["badge"].setText(label)
            data["icon"].setText(glyph_state_map[state])
            set_status_frame(data["row"], state)
            set_status_frame(data["icon_box"], state)
            set_status_badge(data["badge"], state)
            set_status_badge(data["icon"], state)

    def apply_density(self, density: str):
        h = density_button_height(density)
        for data in self._service_widgets.values():
            for key in ("start_btn", "stop_btn", "restart_btn", "open_btn"):
                btn = data.get(key)
                if btn:
                    btn.setFixedHeight(h)
                    repolish(btn)
