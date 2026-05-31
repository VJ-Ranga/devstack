"""First-run welcome dialog shown once when app-settings.json does not yet exist."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)


class FirstRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to DevStack")
        self.setMinimumWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        title = QLabel("Welcome to DevStack 👋")
        title.setStyleSheet("font-size: 18px; font-weight: 800;")
        layout.addWidget(title)

        intro = QLabel(
            "Your portable local web stack is ready.\n"
            "Here's how to get started in under a minute:"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(intro)

        steps = [
            ("1", "Start the stack",       "Go to Control → click Start All"),
            ("2", "Check phpMyAdmin",       "Verify MariaDB is running at /phpmyadmin/"),
            ("3", "Create your first site", "Go to Websites → Install Website"),
            ("4", "Open your site",         "Click Open on any site row to launch it in the browser"),
        ]

        for num, heading, detail in steps:
            row = QHBoxLayout()
            row.setSpacing(12)

            num_lbl = QLabel(num)
            num_lbl.setFixedSize(28, 28)
            num_lbl.setAlignment(Qt.AlignCenter)
            num_lbl.setStyleSheet(
                "background:#E55B3C; color:#fff; border-radius:14px;"
                "font-size:13px; font-weight:800;"
            )
            row.addWidget(num_lbl, 0, Qt.AlignTop)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            h = QLabel(heading)
            h.setStyleSheet("font-size:13px; font-weight:700;")
            d = QLabel(detail)
            d.setStyleSheet("font-size:12px; color:#666;")
            text_col.addWidget(h)
            text_col.addWidget(d)
            row.addLayout(text_col, 1)

            layout.addLayout(row)

        tip = QLabel(
            "💡 Tip: Use the Logs tab to diagnose any service that shows "
            "\"Needs Attention\"."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet(
            "font-size:11px; color:#666; background:#f5f3f0;"
            "border:1px solid #e5e2dc; border-radius:8px; padding:10px 12px;"
        )
        layout.addWidget(tip)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Let's Go →")
        ok_btn.setStyleSheet(
            "background:#E55B3C; color:#fff; border:none; border-radius:6px;"
            "font-size:13px; font-weight:700; padding:8px 24px;"
        )
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)
