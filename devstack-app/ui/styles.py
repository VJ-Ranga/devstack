from pathlib import Path

FONT_FAMILY = '"Segoe UI"'
MONO_FONT = '"Cascadia Code", "Consolas"'

_THEME_PATH = Path(__file__).with_name("theme.qss")


def density_button_height(density: str) -> int:
    return 32 if density == "compact" else 36


def _tab_vpad(density: str) -> int:
    return 8 if density == "compact" else 10


def build_stylesheet(density: str = "comfortable") -> str:
    qss = _THEME_PATH.read_text(encoding="utf-8")
    qss = qss.replace("{{BUTTON_HEIGHT}}", str(density_button_height(density)))
    qss = qss.replace("{{TAB_VPAD}}", str(_tab_vpad(density)))
    return qss


def repolish(widget):
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_status_frame(widget, status: str):
    widget.setProperty("status", status)
    repolish(widget)


def set_status_badge(widget, status: str):
    widget.setProperty("status", status)
    repolish(widget)


FLUENT_GLYPHS = {
    "nginx": "\uE774",
    "apache": "\uE7F4",
    "phpmyadmin": "\uE9D2",
    "dashboard": "\uE80F",
    "running": "\uE73E",
    "stopped": "\uE711",
    "partial": "\uE814",
}
