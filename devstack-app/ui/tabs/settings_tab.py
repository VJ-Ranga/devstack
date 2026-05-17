from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QComboBox

from core.config import DEFAULT_SETTINGS, load_settings, save_settings
from ui.styles import density_button_height, repolish


class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._setup_ui()
        self._load_settings()

    def _make_panel(self, label_text: str):
        label = QLabel(label_text)
        label.setObjectName("SectionLabel")
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        return label, panel, layout

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("TabPage")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Keep settings plain and practical. Save only what the utility actually needs.")
        subtitle.setObjectName("BodyText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        stack_label, stack_panel, stack_layout = self._make_panel("STACK PATH")
        layout.addWidget(stack_label)
        stack_form = QFormLayout()
        stack_form.setSpacing(8)
        self.stack_root_input = QLineEdit()
        self.stack_root_input.setPlaceholderText("Path to devstack-template folder")
        browse_row = QHBoxLayout()
        browse_row.setSpacing(8)
        browse_row.addWidget(self.stack_root_input, 1)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("DefaultButton")
        self.browse_btn.clicked.connect(self._browse_stack_root)
        browse_row.addWidget(self.browse_btn)
        stack_form.addRow("Stack Root", browse_row)
        stack_layout.addLayout(stack_form)
        layout.addWidget(stack_panel)

        ports_label, ports_panel, ports_layout = self._make_panel("PORT CONFIGURATION")
        layout.addWidget(ports_label)
        ports_form = QFormLayout()
        ports_form.setSpacing(8)

        def port_spinbox():
            box = QSpinBox()
            box.setRange(1, 65535)
            box.setFixedWidth(120)
            return box

        self.apache_port_input = port_spinbox()
        self.nginx_port_input = port_spinbox()
        self.php_port_input = port_spinbox()
        self.mysql_port_input = port_spinbox()
        ports_form.addRow("Apache Port", self.apache_port_input)
        ports_form.addRow("Nginx Port", self.nginx_port_input)
        ports_form.addRow("PHP Port", self.php_port_input)
        ports_form.addRow("MySQL Port", self.mysql_port_input)
        ports_layout.addLayout(ports_form)
        layout.addWidget(ports_panel)

        app_label, app_panel, app_layout = self._make_panel("APPLICATION")
        layout.addWidget(app_label)
        app_form = QFormLayout()
        app_form.setSpacing(8)
        self.refresh_interval_input = QSpinBox()
        self.refresh_interval_input.setRange(1, 60)
        self.refresh_interval_input.setSuffix(" seconds")
        self.ui_density_input = QComboBox()
        self.ui_density_input.addItem("Comfortable", "comfortable")
        self.ui_density_input.addItem("Compact", "compact")
        app_form.addRow("Auto Refresh", self.refresh_interval_input)
        app_form.addRow("UI Density", self.ui_density_input)
        app_layout.addLayout(app_form)
        layout.addWidget(app_panel)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._save_settings)
        button_row.addWidget(self.save_btn)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("DefaultButton")
        self.reset_btn.clicked.connect(self._reset_defaults)
        button_row.addWidget(self.reset_btn)
        layout.addLayout(button_row)
        layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def _browse_stack_root(self):
        path = QFileDialog.getExistingDirectory(self, "Select DevStack Root Folder", self.stack_root_input.text())
        if path:
            self.stack_root_input.setText(path)

    def _load_settings(self):
        settings = load_settings()
        self.stack_root_input.setText(settings.get("stack_root", ""))
        self.apache_port_input.setValue(settings.get("apache_port", 8088))
        self.nginx_port_input.setValue(settings.get("nginx_port", 80))
        self.php_port_input.setValue(settings.get("php_port", 9000))
        self.mysql_port_input.setValue(settings.get("mysql_port", 3306))
        self.refresh_interval_input.setValue(settings.get("auto_refresh_interval", 5))
        idx = self.ui_density_input.findData(settings.get("ui_density", "comfortable"))
        self.ui_density_input.setCurrentIndex(idx if idx >= 0 else 0)

    def _save_settings(self):
        stack = self.stack_root_input.text().strip()
        settings = {
            "stack_root": str(Path(stack).resolve()) if stack else stack,
            "apache_port": self.apache_port_input.value(),
            "nginx_port": self.nginx_port_input.value(),
            "php_port": self.php_port_input.value(),
            "mysql_port": self.mysql_port_input.value(),
            "auto_refresh_interval": self.refresh_interval_input.value(),
            "ui_density": self.ui_density_input.currentData(),
        }
        save_settings(settings)
        self.main_window.set_stack_root(settings["stack_root"])
        self.main_window.apply_settings(settings)
        QMessageBox.information(self, "Saved", "Settings saved.")

    def _reset_defaults(self):
        save_settings(DEFAULT_SETTINGS)
        self._load_settings()
        self.main_window.set_stack_root(DEFAULT_SETTINGS["stack_root"])
        self.main_window.apply_settings(DEFAULT_SETTINGS)
        QMessageBox.information(self, "Reset", "Default settings restored.")

    def apply_density(self, density: str):
        h = density_button_height(density)
        for btn in (self.browse_btn, self.save_btn, self.reset_btn):
            btn.setFixedHeight(h)
            repolish(btn)
