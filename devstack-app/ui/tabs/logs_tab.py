from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from core.log_reader import get_log, get_log_sources
from ui.styles import MONO_FONT, density_button_height, repolish  # MONO_FONT is a single family name


class LogsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._sources = get_log_sources()
        self._raw_log = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Logs")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Inspect output streams for Nginx and MariaDB.")
        subtitle.setObjectName("BodyText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        controls_label = QLabel("LOG SOURCE")
        controls_label.setObjectName("SectionLabel")
        layout.addWidget(controls_label)

        # ── Source + refresh controls ─────────────────────────────────────
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
        self.source_combo.currentIndexChanged.connect(self._load_log)
        controls_layout.addWidget(self.source_combo)

        self.auto_refresh_cb = QCheckBox("Auto-refresh (3 s)")
        self.auto_refresh_cb.setToolTip("Reload the selected log every 3 seconds")
        self.auto_refresh_cb.toggled.connect(self._toggle_auto_refresh)
        controls_layout.addWidget(self.auto_refresh_cb)

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

        # ── Search / filter bar ───────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter log output... (case-insensitive)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_input)

        self.match_label = QLabel("")
        self.match_label.setObjectName("MetaText")
        self.match_label.setFixedWidth(100)
        search_row.addWidget(self.match_label)

        layout.addLayout(search_row)

        # ── Log viewer ────────────────────────────────────────────────────
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont(MONO_FONT, 10))
        self.log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_view.setPlainText("Select a log source above — it will load automatically.")
        layout.addWidget(self.log_view, 1)

        # ── Auto-refresh timer ────────────────────────────────────────────
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(3000)
        self._auto_timer.timeout.connect(self._load_log)

    # ── Public API ────────────────────────────────────────────────────────

    def load_current(self):
        """Called by MainWindow when this tab is switched to."""
        self._load_log()

    # ── Internal ──────────────────────────────────────────────────────────

    def _load_log(self):
        key = self.source_combo.currentData()
        if not key:
            return
        self._raw_log = (
            get_log(self.main_window.get_stack_root(), key, n=300)
            or "No log entries found."
        )
        self._apply_filter(self.search_input.text())

    def _apply_filter(self, text: str):
        if not text.strip():
            self.log_view.setPlainText(self._raw_log)
            self.match_label.setText("")
            return
        lines = self._raw_log.splitlines()
        matched = [ln for ln in lines if text.lower() in ln.lower()]
        self.match_label.setText(f"{len(matched)} match{'es' if len(matched) != 1 else ''}")
        self.log_view.setPlainText(
            "\n".join(matched) if matched else f"(no lines matching '{text}')"
        )
        # Scroll to bottom so newest matches are visible
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def _clear_log(self):
        self._raw_log = ""
        self.log_view.setPlainText("Log cleared. Click Refresh to reload.")
        self.match_label.setText("")

    def _toggle_auto_refresh(self, enabled: bool):
        if enabled:
            self._auto_timer.start()
            self._load_log()
        else:
            self._auto_timer.stop()

    def apply_density(self, density: str):
        h = density_button_height(density)
        for btn in (self.refresh_btn, self.clear_btn):
            btn.setFixedHeight(h)
            repolish(btn)
