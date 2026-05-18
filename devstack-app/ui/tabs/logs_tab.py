from PySide6.QtGui import QFont
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from core.log_reader import get_log, get_log_sources
from ui.styles import MONO_FONT, density_button_height, repolish


class LogsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._sources = get_log_sources()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Logs")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Logs stay secondary. Load them only when you need to inspect a problem.")
        subtitle.setObjectName("BodyText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        controls_label = QLabel("LOG SOURCE")
        controls_label.setObjectName("SectionLabel")
        layout.addWidget(controls_label)

        controls_panel = QFrame()
        controls_panel.setObjectName("Panel")
        controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(16, 12, 16, 12)
        controls_layout.setSpacing(8)

        source_label = QLabel("Source")
        source_label.setObjectName("MetaText")
        controls_layout.addWidget(source_label)

        self.source_combo = QComboBox()
        for src in self._sources:
            self.source_combo.addItem(src["name"], src["key"])
        controls_layout.addWidget(self.source_combo)
        controls_layout.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("DefaultButton")
        self.refresh_btn.clicked.connect(self._load_log)
        controls_layout.addWidget(self.refresh_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("DefaultButton")
        self.clear_btn.clicked.connect(self._clear_log)
        controls_layout.addWidget(self.clear_btn)
        layout.addWidget(controls_panel)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont(MONO_FONT, 10))
        self.log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_view.setPlainText("Select a log source and click Refresh.")
        layout.addWidget(self.log_view, 1)

    def _load_log(self):
        key = self.source_combo.currentData()
        if not key:
            return
        self.log_view.setPlainText(get_log(self.main_window.get_stack_root(), key, n=200) or "No log entries found.")

    def _clear_log(self):
        self.log_view.setPlainText("Select a log source and click Refresh.")

    def apply_density(self, density: str):
        h = density_button_height(density)
        for btn in (self.refresh_btn, self.clear_btn):
            btn.setFixedHeight(h)
            repolish(btn)
