import sys
import os
import traceback
from datetime import datetime
from pathlib import Path

# Enable proper Windows taskbar icon rendering
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("vjranga.devstack.manager.v1")
    except Exception:
        pass

# Suppress Qt's DirectWrite warning for ancient bitmap fonts (e.g. 8514oem)
# that Windows ships for legacy compatibility but which Qt cannot load via
# the modern DirectWrite API. The warning is harmless — we never use those fonts.
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.warning=false")

from PySide6.QtWidgets import QApplication, QStyleFactory, QMessageBox
from PySide6.QtGui import QIcon, QPalette, QColor

from core.config import load_settings
from ui.main_window import MainWindow


def main():
    def _global_excepthook(exc_type, exc_value, exc_tb):
        app_root = Path(__file__).resolve().parents[1]
        log_dir = app_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        crash_log = log_dir / "crash.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stack_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        with crash_log.open("a", encoding="utf-8") as fh:
            fh.write(f"\n[{timestamp}] Unhandled exception\n")
            fh.write(stack_text)
            fh.write("\n")
        traceback.print_exception(exc_type, exc_value, exc_tb)
        try:
            QMessageBox.critical(
                None,
                "Unexpected Error",
                "DevStack hit an unexpected error and wrote details to:\n"
                f"{crash_log}\n\n"
                "Please restart the app."
            )
        except Exception:
            pass
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

    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    icon_ico = os.path.join(assets_dir, "icon.ico")
    icon_png = os.path.join(assets_dir, "icon.png")
    if os.path.exists(icon_ico):
        app.setWindowIcon(QIcon(icon_ico))
    elif os.path.exists(icon_png):
        app.setWindowIcon(QIcon(icon_png))

    window = MainWindow()
    window.show()

    # Show one-time welcome checklist on very first launch
    from core.config import APP_SETTINGS_PATH
    if not APP_SETTINGS_PATH.exists():
        from ui.dialogs.first_run_dialog import FirstRunDialog
        FirstRunDialog(window).exec()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
