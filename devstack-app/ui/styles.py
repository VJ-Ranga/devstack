from pathlib import Path

FONT_FAMILY = '"Segoe UI"'
MONO_FONT = '"Cascadia Code", "Consolas"'

_THEME_PATH = Path(__file__).with_name("theme.qss")


def density_button_height(density: str) -> int:
    return 32 if density == "compact" else 36


def _tab_vpad(density: str) -> int:
    return 8 if density == "compact" else 10


def build_stylesheet(density: str = "comfortable", theme: str = "light") -> str:
    theme_file = f"theme_{theme}.qss"
    path = Path(__file__).with_name(theme_file)
    if not path.exists():
        path = Path(__file__).with_name("theme_light.qss")
    qss = path.read_text(encoding="utf-8")
    
    # Resolve absolute path to assets directory and convert to forward slashes for Qt CSS
    assets_dir = Path(__file__).parents[1] / "assets"
    assets_path = assets_dir.as_posix()
    qss = qss.replace("{{ASSETS_PATH}}", assets_path)
    
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
    "nginx": "N",
    "apache": "A",
    "phpmyadmin": "DB",
    "dashboard": "W",
    "running": "OK",
    "stopped": "X",
    "partial": "!",
}
