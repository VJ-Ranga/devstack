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
)
from core.config import load_settings, save_settings


class CustomizeUIDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.settings = load_settings()
        self.setWindowTitle("Customize UI Design System")
        self.resize(520, 600)
        self.setMinimumSize(480, 520)

        # Style the dialog matching our theme
        theme = self.settings.get("theme", "light")
        bg_col = "#151413" if theme == "dark" else "#F5F3F0"
        card_bg = "#201E1D" if theme == "dark" else "#FFFFFF"
        text_col = "#F5F3F0" if theme == "dark" else "#1E1B18"
        border_col = "#2D2A28" if theme == "dark" else "#E5E2DC"
        accent_col = self.settings.get("accent_color", "#E55B3C")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
                color: {text_col};
            }}
            QLabel {{
                color: {text_col};
            }}
            QLineEdit, QSpinBox {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 4px 8px;
                color: {text_col};
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header
        header = QLabel("Customize System Layout & Colors")
        header.setStyleSheet("font-size: 16px; font-weight: 800; color: #E55B3C;")
        layout.addWidget(header)

        sub = QLabel("Modify process bounds, padding rules, border shapes, and custom accent/canvas colors.")
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 11px; color: #8C8780;")
        layout.addWidget(sub)

        # 2. Scrollable Form area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent;")
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 10, 0)
        form_layout.setSpacing(10)

        # --- Section: Dimensions ---
        dim_lbl = QLabel("WINDOW DIMENSION BOUNDS")
        dim_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #E55B3C; margin-top: 10px;")
        form_layout.addRow(dim_lbl)

        self.min_w = QSpinBox()
        self.min_w.setRange(400, 3000)
        self.min_w.setValue(self.settings.get("min_width", 800))
        form_layout.addRow("Minimum Width (px):", self.min_w)

        self.min_h = QSpinBox()
        self.min_h.setRange(300, 2000)
        self.min_h.setValue(self.settings.get("min_height", 560))
        form_layout.addRow("Minimum Height (px):", self.min_h)

        self.max_w = QSpinBox()
        self.max_w.setRange(800, 5000)
        self.max_w.setValue(self.settings.get("max_width", 2000))
        form_layout.addRow("Maximum Width (px):", self.max_w)

        self.max_h = QSpinBox()
        self.max_h.setRange(600, 4000)
        self.max_h.setValue(self.settings.get("max_height", 2000))
        form_layout.addRow("Maximum Height (px):", self.max_h)

        # --- Section: Sizing & Spacing ---
        size_lbl = QLabel("FONT SIZING, PADDING & MARGIN GAP RULES")
        size_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #E55B3C; margin-top: 15px;")
        form_layout.addRow(size_lbl)

        self.font_size = QSpinBox()
        self.font_size.setRange(10, 22)
        self.font_size.setValue(self.settings.get("base_font_size", 13))
        form_layout.addRow("Base UI Font Size (pt):", self.font_size)

        self.card_radius = QSpinBox()
        self.card_radius.setRange(0, 36)
        self.card_radius.setValue(self.settings.get("card_radius", 16))
        form_layout.addRow("Card Panel Corner Radius (px):", self.card_radius)

        self.btn_radius = QSpinBox()
        self.btn_radius.setRange(0, 24)
        self.btn_radius.setValue(self.settings.get("btn_radius", 8))
        form_layout.addRow("Button Corner Radius (px):", self.btn_radius)

        self.btn_height = QSpinBox()
        self.btn_height.setRange(20, 60)
        self.btn_height.setValue(self.settings.get("btn_height", 32))
        form_layout.addRow("Buttons Minimum Height (px):", self.btn_height)

        self.btn_pad_v = QSpinBox()
        self.btn_pad_v.setRange(0, 20)
        self.btn_pad_v.setValue(self.settings.get("btn_padding_v", 4))
        form_layout.addRow("Button Vertical Padding (px):", self.btn_pad_v)

        self.btn_pad_h = QSpinBox()
        self.btn_pad_h.setRange(0, 40)
        self.btn_pad_h.setValue(self.settings.get("btn_padding_h", 12))
        form_layout.addRow("Button Horizontal Padding (px):", self.btn_pad_h)

        self.btn_margin_v = QSpinBox()
        self.btn_margin_v.setRange(0, 16)
        self.btn_margin_v.setValue(self.settings.get("btn_margin_v", 3))
        form_layout.addRow("Sidebar Button Margin Gap (px):", self.btn_margin_v)

        # --- Section: Color Picker Accents ---
        color_lbl = QLabel("COLOR SCHEMES & BRAND ACCENTS")
        color_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #E55B3C; margin-top: 15px;")
        form_layout.addRow(color_lbl)

        # Primary Accent Color Row
        self.accent_color_input = QLineEdit(self.settings.get("accent_color", "#E55B3C"))
        pick_accent_btn = QPushButton("Pick")
        pick_accent_btn.setFixedWidth(50)
        pick_accent_btn.clicked.connect(lambda: self._pick_color(self.accent_color_input, "Primary Accent Theme Color"))
        accent_layout = QHBoxLayout()
        accent_layout.addWidget(self.accent_color_input)
        accent_layout.addWidget(pick_accent_btn)
        form_layout.addRow("Brand Accent Color (Hex):", accent_layout)

        # Sidebar BG Color Row
        self.sidebar_bg_input = QLineEdit(self.settings.get("sidebar_bg_color", ""))
        self.sidebar_bg_input.setPlaceholderText("Default")
        pick_sidebar_btn = QPushButton("Pick")
        pick_sidebar_btn.setFixedWidth(50)
        pick_sidebar_btn.clicked.connect(lambda: self._pick_color(self.sidebar_bg_input, "Sidebar Background Color"))
        sidebar_layout = QHBoxLayout()
        sidebar_layout.addWidget(self.sidebar_bg_input)
        sidebar_layout.addWidget(pick_sidebar_btn)
        form_layout.addRow("Sidebar Background (Hex):", sidebar_layout)

        # Canvas BG Color Row
        self.app_bg_input = QLineEdit(self.settings.get("app_bg_color", ""))
        self.app_bg_input.setPlaceholderText("Default")
        pick_app_btn = QPushButton("Pick")
        pick_app_btn.setFixedWidth(50)
        pick_app_btn.clicked.connect(lambda: self._pick_color(self.app_bg_input, "Application Main Canvas Background"))
        app_layout = QHBoxLayout()
        app_layout.addWidget(self.app_bg_input)
        app_layout.addWidget(pick_app_btn)
        form_layout.addRow("Main Canvas BG (Hex):", app_layout)

        # Card BG Color Row
        self.card_bg_input = QLineEdit(self.settings.get("card_bg_color", ""))
        self.card_bg_input.setPlaceholderText("Default")
        pick_card_btn = QPushButton("Pick")
        pick_card_btn.setFixedWidth(50)
        pick_card_btn.clicked.connect(lambda: self._pick_color(self.card_bg_input, "Card Background Color"))
        card_layout = QHBoxLayout()
        card_layout.addWidget(self.card_bg_input)
        card_layout.addWidget(pick_card_btn)
        form_layout.addRow("Cards Background (Hex):", card_layout)

        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)

        # 3. Actions Row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        reset_btn = QPushButton("Reset Defaults")
        reset_btn.setStyleSheet("""
            background-color: transparent; 
            border: 1px solid rgba(130, 130, 130, 0.4); 
            color: #8C8780;
        """)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_defaults)
        actions_layout.addWidget(reset_btn)

        actions_layout.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            background-color: transparent; 
            border: 1px solid rgba(130, 130, 130, 0.4);
        """)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        actions_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply Customizations")
        apply_btn.setStyleSheet(f"background-color: {accent_col}; color: #FFFFFF; border: none;")
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_customizations)
        actions_layout.addWidget(apply_btn)

        layout.addLayout(actions_layout)

    def _pick_color(self, target_line_edit, label):
        current_color = target_line_edit.text() if target_line_edit.text().startswith("#") else "#E55B3C"
        color = QColorDialog.getColor(current_color, self, f"Select {label}")
        if color.isValid():
            target_line_edit.setText(color.name().upper())

    def _reset_defaults(self):
        confirm = QMessageBox.question(
            self,
            "Reset UI?",
            "Are you sure you want to restore the default warm ivory / clay terracotta developer design system values?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            defaults = {
                "min_width": 800,
                "min_height": 560,
                "max_width": 2000,
                "max_height": 2000,
                "accent_color": "#E55B3C",
                "sidebar_bg_color": "",
                "app_bg_color": "",
                "card_bg_color": "",
                "card_radius": 16,
                "btn_radius": 8,
                "btn_height": 32,
                "btn_padding_v": 4,
                "btn_padding_h": 12,
                "btn_margin_v": 3,
                "base_font_size": 13,
            }
            self.settings.update(defaults)
            save_settings(self.settings)

            # Update dialog fields instantly
            self.min_w.setValue(800)
            self.min_h.setValue(560)
            self.max_w.setValue(2000)
            self.max_h.setValue(2000)
            self.font_size.setValue(13)
            self.card_radius.setValue(16)
            self.btn_radius.setValue(8)
            self.btn_height.setValue(32)
            self.btn_pad_v.setValue(4)
            self.btn_pad_h.setValue(12)
            self.btn_margin_v.setValue(3)
            self.accent_color_input.setText("#E55B3C")
            self.sidebar_bg_input.setText("")
            self.app_bg_input.setText("")
            self.card_bg_input.setText("")

            # Propagate style changes to Main Window
            self.main_window.setMinimumSize(800, 560)
            self.main_window.setMaximumSize(2000, 2000)
            self.main_window.apply_settings(self.settings)
            QMessageBox.information(self, "Styles Reset", "UI design token defaults successfully re-applied.")
            self.accept()

    def _apply_customizations(self):
        # Update bounds values
        self.settings["min_width"] = self.min_w.value()
        self.settings["min_height"] = self.min_h.value()
        self.settings["max_width"] = self.max_w.value()
        self.settings["max_height"] = self.max_h.value()

        # Update styling spacing & sizes values
        self.settings["base_font_size"] = self.font_size.value()
        self.settings["card_radius"] = self.card_radius.value()
        self.settings["btn_radius"] = self.btn_radius.value()
        self.settings["btn_height"] = self.btn_height.value()
        self.settings["btn_padding_v"] = self.btn_pad_v.value()
        self.settings["btn_padding_h"] = self.btn_pad_h.value()
        self.settings["btn_margin_v"] = self.btn_margin_v.value()

        # Update dynamic colors
        accent = self.accent_color_input.text().strip().upper()
        if accent and not accent.startswith("#"):
            accent = "#" + accent
        self.settings["accent_color"] = accent if len(accent) == 7 else "#E55B3C"

        sidebar = self.sidebar_bg_input.text().strip().upper()
        if sidebar and not sidebar.startswith("#"):
            sidebar = "#" + sidebar
        self.settings["sidebar_bg_color"] = sidebar if len(sidebar) == 7 else ""

        app_bg = self.app_bg_input.text().strip().upper()
        if app_bg and not app_bg.startswith("#"):
            app_bg = "#" + app_bg
        self.settings["app_bg_color"] = app_bg if len(app_bg) == 7 else ""

        card_bg = self.card_bg_input.text().strip().upper()
        if card_bg and not card_bg.startswith("#"):
            card_bg = "#" + card_bg
        self.settings["card_bg_color"] = card_bg if len(card_bg) == 7 else ""

        # Persist dynamic UI settings
        save_settings(self.settings)

        # Propagate changes to parent MainWindow instantly
        self.main_window.setMinimumSize(self.settings["min_width"], self.settings["min_height"])
        self.main_window.setMaximumSize(self.settings["max_width"], self.settings["max_height"])
        self.main_window.apply_settings(self.settings)

        self.accept()
