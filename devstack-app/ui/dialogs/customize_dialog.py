from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QColorDialog,
    QMessageBox,
    QScrollArea,
    QWidget,
    QFrame,
    QCheckBox,
)
from core.config import load_settings, save_settings

# ── WinUI 3 design-token defaults ─────────────────────────────────────────────
_DEFAULTS = {
    "min_width":        800,
    "min_height":       560,
    "max_width":        16777215,
    "max_height":       16777215,
    "base_font_size":   14,
    "card_radius":      8,
    "btn_radius":       4,
    "btn_height":       25,
    "accent_color":     "#E55B3C",
    "sidebar_bg_color": "",
    "app_bg_color":     "",
    "card_bg_color":    "",
}


class CustomizeUIDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.settings = load_settings()
        self.setWindowTitle("Customize UI Design System")
        self.resize(520, 620)
        self.setMinimumSize(480, 520)

        theme      = self.settings.get("theme", "light")
        is_dark    = theme == "dark"
        bg_col     = "#202020"   if is_dark else "#F3F3F3"
        card_bg    = "#2C2C2C"   if is_dark else "#FFFFFF"
        text_col   = "#FFFFFF"   if is_dark else "#1C1C1C"
        muted_col  = "#9C9C9C"   if is_dark else "#767676"
        border_col = "rgba(255,255,255,0.10)" if is_dark else "rgba(0,0,0,0.10)"
        accent_col = self.settings.get("accent_color", "#E55B3C")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
                color: {text_col};
            }}
            QLabel {{ color: {text_col}; background: transparent; }}
            QLineEdit, QSpinBox {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 4px;
                padding: 5px 10px;
                min-height: 32px;
                color: {text_col};
                font-size: 13px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 2px solid {accent_col};
            }}
            QCheckBox {{ color: {text_col}; }}
            QScrollBar:vertical {{
                border: none; background: transparent; width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(128,128,128,0.25); border-radius: 3px; min-height: 20px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────
        header = QLabel("Customize System Layout & Colors")
        header.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {accent_col};")
        layout.addWidget(header)

        sub = QLabel("Adjust font size, spacing, border radii, and accent/background colors.")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"font-size: 12px; color: {muted_col};")
        layout.addWidget(sub)

        # ── Scrollable form ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent;")
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 12, 0)
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        def section(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"font-size: 10px; font-weight: 700; color: {accent_col};"
                "letter-spacing: 0.5px; margin-top: 14px;"
            )
            form_layout.addRow(lbl)

        # ── Window bounds ─────────────────────────────────────────────
        section("WINDOW SIZE BOUNDS")

        self.min_w = QSpinBox()
        self.min_w.setRange(400, 3000)
        self.min_w.setValue(self.settings.get("min_width", _DEFAULTS["min_width"]))
        form_layout.addRow("Minimum Width (px):", self.min_w)

        self.min_h = QSpinBox()
        self.min_h.setRange(300, 2000)
        self.min_h.setValue(self.settings.get("min_height", _DEFAULTS["min_height"]))
        form_layout.addRow("Minimum Height (px):", self.min_h)

        has_max = self.settings.get("max_width", 16777215) < 16777215
        self.limit_max_cb = QCheckBox("Apply maximum size limit")
        self.limit_max_cb.setChecked(has_max)
        form_layout.addRow("", self.limit_max_cb)

        self.max_w = QSpinBox()
        self.max_w.setRange(800, 5000)
        self.max_w.setValue(self.settings.get("max_width", 2000) if has_max else 2000)
        self.max_w.setEnabled(has_max)
        form_layout.addRow("Maximum Width (px):", self.max_w)

        self.max_h = QSpinBox()
        self.max_h.setRange(600, 4000)
        self.max_h.setValue(self.settings.get("max_height", 2000) if has_max else 2000)
        self.max_h.setEnabled(has_max)
        form_layout.addRow("Maximum Height (px):", self.max_h)

        self.limit_max_cb.toggled.connect(self.max_w.setEnabled)
        self.limit_max_cb.toggled.connect(self.max_h.setEnabled)

        # ── Typography & spacing ──────────────────────────────────────
        section("TYPOGRAPHY & SPACING")

        self.font_size = QSpinBox()
        self.font_size.setRange(10, 22)
        self.font_size.setValue(self.settings.get("base_font_size", _DEFAULTS["base_font_size"]))
        form_layout.addRow("Base Font Size (px):", self.font_size)

        self.card_radius = QSpinBox()
        self.card_radius.setRange(0, 24)
        self.card_radius.setValue(self.settings.get("card_radius", _DEFAULTS["card_radius"]))
        form_layout.addRow("Card Corner Radius (px):", self.card_radius)

        self.btn_radius = QSpinBox()
        self.btn_radius.setRange(0, 16)
        self.btn_radius.setValue(self.settings.get("btn_radius", _DEFAULTS["btn_radius"]))
        form_layout.addRow("Button Corner Radius (px):", self.btn_radius)

        self.btn_height = QSpinBox()
        self.btn_height.setRange(24, 56)
        self.btn_height.setValue(self.settings.get("btn_height", _DEFAULTS["btn_height"]))
        form_layout.addRow("Button Height (px):", self.btn_height)

        # ── Colors ────────────────────────────────────────────────────
        section("COLOR SCHEMES & BRAND ACCENTS")

        self.accent_input = QLineEdit(self.settings.get("accent_color", _DEFAULTS["accent_color"]))
        pick_accent = QPushButton("Pick")
        pick_accent.setFixedWidth(52)
        pick_accent.setStyleSheet(f"background:{card_bg}; border:1px solid {border_col}; border-radius:4px; color:{text_col};")
        pick_accent.clicked.connect(lambda: self._pick_color(self.accent_input, "Accent Color"))
        row = QHBoxLayout(); row.setSpacing(6)
        row.addWidget(self.accent_input); row.addWidget(pick_accent)
        form_layout.addRow("Accent Color (Hex):", row)

        self.sidebar_bg_input = QLineEdit(self.settings.get("sidebar_bg_color", ""))
        self.sidebar_bg_input.setPlaceholderText("Default")
        pick_sb = QPushButton("Pick"); pick_sb.setFixedWidth(52)
        pick_sb.setStyleSheet(f"background:{card_bg}; border:1px solid {border_col}; border-radius:4px; color:{text_col};")
        pick_sb.clicked.connect(lambda: self._pick_color(self.sidebar_bg_input, "Sidebar Background"))
        row2 = QHBoxLayout(); row2.setSpacing(6)
        row2.addWidget(self.sidebar_bg_input); row2.addWidget(pick_sb)
        form_layout.addRow("Sidebar Background (Hex):", row2)

        self.app_bg_input = QLineEdit(self.settings.get("app_bg_color", ""))
        self.app_bg_input.setPlaceholderText("Default")
        pick_ab = QPushButton("Pick"); pick_ab.setFixedWidth(52)
        pick_ab.setStyleSheet(f"background:{card_bg}; border:1px solid {border_col}; border-radius:4px; color:{text_col};")
        pick_ab.clicked.connect(lambda: self._pick_color(self.app_bg_input, "Main Background"))
        row3 = QHBoxLayout(); row3.setSpacing(6)
        row3.addWidget(self.app_bg_input); row3.addWidget(pick_ab)
        form_layout.addRow("Main Background (Hex):", row3)

        self.card_bg_input = QLineEdit(self.settings.get("card_bg_color", ""))
        self.card_bg_input.setPlaceholderText("Default")
        pick_cb = QPushButton("Pick"); pick_cb.setFixedWidth(52)
        pick_cb.setStyleSheet(f"background:{card_bg}; border:1px solid {border_col}; border-radius:4px; color:{text_col};")
        pick_cb.clicked.connect(lambda: self._pick_color(self.card_bg_input, "Card Background"))
        row4 = QHBoxLayout(); row4.setSpacing(6)
        row4.addWidget(self.card_bg_input); row4.addWidget(pick_cb)
        form_layout.addRow("Card Background (Hex):", row4)

        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)

        # ── Action buttons ────────────────────────────────────────────
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.HLine)
        sep_line.setStyleSheet(f"color: {border_col};")
        layout.addWidget(sep_line)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        reset_btn = QPushButton("Reset Defaults")
        reset_btn.setStyleSheet(
            f"background:transparent; border:1px solid {border_col}; "
            f"color:{muted_col}; border-radius:4px; padding:5px 14px;"
        )
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_defaults)
        actions.addWidget(reset_btn)

        actions.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            f"background:transparent; border:1px solid {border_col}; "
            f"color:{text_col}; border-radius:4px; padding:5px 14px;"
        )
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply Customizations")
        apply_btn.setStyleSheet(
            f"background:{accent_col}; color:#FFFFFF; border:none; "
            f"border-radius:4px; padding:5px 16px; font-weight:600;"
        )
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_customizations)
        actions.addWidget(apply_btn)

        layout.addLayout(actions)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pick_color(self, target: QLineEdit, label: str):
        current = target.text() if target.text().startswith("#") else "#E55B3C"
        color = QColorDialog.getColor(current, self, f"Select {label}")
        if color.isValid():
            target.setText(color.name().upper())

    def _reset_defaults(self):
        if QMessageBox.question(
            self, "Reset to Defaults",
            "Reset all UI customizations back to the WinUI 3 design system defaults?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        self.settings.update(_DEFAULTS)
        save_settings(self.settings)

        # Sync all spinboxes / inputs
        self.min_w.setValue(_DEFAULTS["min_width"])
        self.min_h.setValue(_DEFAULTS["min_height"])
        self.limit_max_cb.setChecked(False)
        self.max_w.setValue(2000)
        self.max_h.setValue(2000)
        self.font_size.setValue(_DEFAULTS["base_font_size"])
        self.card_radius.setValue(_DEFAULTS["card_radius"])
        self.btn_radius.setValue(_DEFAULTS["btn_radius"])
        self.btn_height.setValue(_DEFAULTS["btn_height"])
        self.accent_input.setText(_DEFAULTS["accent_color"])
        self.sidebar_bg_input.setText("")
        self.app_bg_input.setText("")
        self.card_bg_input.setText("")

        self.main_window.setMinimumSize(800, 560)
        self.main_window.setMaximumSize(16777215, 16777215)
        self.main_window.apply_settings(self.settings)
        QMessageBox.information(self, "Reset Complete", "UI defaults restored successfully.")
        self.accept()

    def _apply_customizations(self):
        self.settings["min_width"]  = self.min_w.value()
        self.settings["min_height"] = self.min_h.value()
        self.settings["max_width"]  = self.max_w.value() if self.limit_max_cb.isChecked() else 16777215
        self.settings["max_height"] = self.max_h.value() if self.limit_max_cb.isChecked() else 16777215

        self.settings["base_font_size"] = self.font_size.value()
        self.settings["card_radius"]    = self.card_radius.value()
        self.settings["btn_radius"]     = self.btn_radius.value()
        self.settings["btn_height"]     = self.btn_height.value()

        def _clean_hex(val, fallback=""):
            v = val.strip().upper()
            if not v.startswith("#"):
                v = "#" + v
            return v if len(v) == 7 else fallback

        self.settings["accent_color"]     = _clean_hex(self.accent_input.text(), "#E55B3C")
        self.settings["sidebar_bg_color"] = _clean_hex(self.sidebar_bg_input.text())
        self.settings["app_bg_color"]     = _clean_hex(self.app_bg_input.text())
        self.settings["card_bg_color"]    = _clean_hex(self.card_bg_input.text())

        save_settings(self.settings)

        self.main_window.setMinimumSize(self.settings["min_width"], self.settings["min_height"])
        if self.settings["max_width"] < 16777215:
            self.main_window.setMaximumSize(self.settings["max_width"], self.settings["max_height"])
        else:
            self.main_window.setMaximumSize(16777215, 16777215)
        self.main_window.apply_settings(self.settings)
        self.accept()
