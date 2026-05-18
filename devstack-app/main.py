import sys
import os
import traceback

# Enable proper Windows taskbar icon rendering
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("vjranga.devstack.manager.v1")
    except Exception:
        pass

from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtGui import QIcon, QPalette, QColor

from core.config import load_settings
from ui.main_window import MainWindow


def main():
    def _global_excepthook(exc_type, exc_value, exc_tb):
        traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.excepthook = _global_excepthook

    app = QApplication(sys.argv)
    styles = {name.lower(): name for name in QStyleFactory.keys()}
    if "windowsvista" in styles:
        app.setStyle(styles["windowsvista"])
    elif "windows" in styles:
        app.setStyle(styles["windows"])
    else:
        app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f3f3f3"))
    palette.setColor(QPalette.WindowText, QColor("#1f1f1f"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#fbfbfb"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#1f1f1f"))
    palette.setColor(QPalette.Text, QColor("#1f1f1f"))
    palette.setColor(QPalette.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ButtonText, QColor("#1f1f1f"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#0f6cbd"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    app.setApplicationName("DevStack Manager")
    app.setOrganizationName("DevStack")

    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
