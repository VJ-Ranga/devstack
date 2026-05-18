from pathlib import Path
from core.config import load_settings

FONT_FAMILY = '"Segoe UI"'
MONO_FONT = '"Cascadia Code", "Consolas"'

_THEME_PATH = Path(__file__).with_name("theme.qss")


def density_button_height(density: str) -> int:
    return 28 if density == "compact" else 32


def _tab_vpad(density: str) -> int:
    return 6 if density == "compact" else 8


def _adjust_hex_color(hex_str: str, amount: int) -> str:
    """Adjust hex color brightness by amount (-255 to 255)."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) != 6:
        return "#E55B3C"  # fallback
    try:
        r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        return f"#{r:02X}{g:02X}{b:02X}"
    except ValueError:
        return "#E55B3C"


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
    
    # Load dynamic UI customizations from settings.json
    settings = load_settings()
    
    # 1. Custom Button Height / Paddings
    btn_height = settings.get("btn_height", density_button_height(density))
    qss = qss.replace("{{BUTTON_HEIGHT}}", str(btn_height))
    
    # Custom Button Padding / Spacing inside the QSS
    btn_padding_v = settings.get("btn_padding_v", 4)
    btn_padding_h = settings.get("btn_padding_h", 12)
    qss = qss.replace("padding: 4px 12px;", f"padding: {btn_padding_v}px {btn_padding_h}px;")
    
    # Button Margin gaps
    btn_margin_v = settings.get("btn_margin_v", 3)
    btn_margin_h = settings.get("btn_margin_h", 12)
    qss = qss.replace("margin: 3px 12px;", f"margin: {btn_margin_v}px {btn_margin_h}px;")
    
    qss = qss.replace("{{TAB_VPAD}}", str(_tab_vpad(density)))
    
    # 2. Custom Primary Accent Color (Orange theme color replacement)
    accent_color = settings.get("accent_color", "#E55B3C")
    hover_color = _adjust_hex_color(accent_color, -20)
    pressed_color = _adjust_hex_color(accent_color, -40)
    
    qss = qss.replace("#E55B3C", accent_color)
    qss = qss.replace("#CC4E30", hover_color)
    qss = qss.replace("#B23F23", pressed_color)
    # Also adjust secondary accent buttons (like Nginx/MariaDB badges, etc.)
    qss = qss.replace("#D94E34", _adjust_hex_color(accent_color, -10))
    
    # 3. Custom Window Backgrounds
    custom_bg = settings.get("app_bg_color", "")
    custom_sidebar = settings.get("sidebar_bg_color", "")
    custom_card = settings.get("card_bg_color", "")
    
    if theme == "light":
        if custom_bg:
            qss = qss.replace("#F5F3F0", custom_bg)
        if custom_sidebar:
            qss = qss.replace("#EBEBE6", custom_sidebar)
        if custom_card:
            qss = qss.replace("#FFFFFF", custom_card)
    else: # dark theme
        if custom_bg:
            qss = qss.replace("#151413", custom_bg)
        if custom_sidebar:
            qss = qss.replace("#0C0B0A", custom_sidebar)
        if custom_card:
            qss = qss.replace("#201E1D", custom_card)
            
    # 4. Custom Border Radius
    card_radius = settings.get("card_radius", 16)
    btn_radius = settings.get("btn_radius", 8)
    qss = qss.replace("border-radius: 16px;", f"border-radius: {card_radius}px;")
    qss = qss.replace("border-radius: 10px;", f"border-radius: {int(card_radius*0.6)}px;")
    qss = qss.replace("border-radius: 8px;", f"border-radius: {btn_radius}px;")
    qss = qss.replace("border-radius: 6px;", f"border-radius: {int(btn_radius*0.75)}px;")
    
    # 5. Custom Font Size
    base_font_size = settings.get("base_font_size", 13)
    qss = qss.replace("font-size: 13px;", f"font-size: {base_font_size}px;")
    qss = qss.replace("font-size: 12px;", f"font-size: {base_font_size-1}px;")
    qss = qss.replace("font-size: 11px;", f"font-size: {max(9, base_font_size-2)}px;")
    qss = qss.replace("font-size: 15px;", f"font-size: {base_font_size+2}px;")
    qss = qss.replace("font-size: 26px;", f"font-size: {base_font_size+13}px;")
    
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
