from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ui.styles import FLUENT_GLYPHS, repolish


class ClickableFrame(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, event):
        self._hover = True
        self.setProperty("hover", "true")
        repolish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.setProperty("hover", "false")
        repolish(self)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class QuickAccessCard(ClickableFrame):
    def __init__(self, title: str, subtitle: str, glyph_key: str, parent=None):
        super().__init__(parent)
        self.setObjectName("QuickAccessCard")
        self.setProperty("hover", "false")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        icon_box = QFrame()
        icon_box.setObjectName("QuickAccessIconBox")
        icon_box.setFixedSize(36, 36)
        icon_layout = QVBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        icon_label = QLabel(FLUENT_GLYPHS[glyph_key])
        icon_label.setObjectName("QuickAccessIconGlyph")
        icon_layout.addWidget(icon_label)
        layout.addWidget(icon_box)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("QuickAccessTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("QuickAccessSubtitle")
        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)
        layout.addLayout(text_layout, 1)
