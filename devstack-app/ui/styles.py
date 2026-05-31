from pathlib import Path
from core.config import load_settings

MONO_FONT = "Consolas"


def density_button_height(density: str) -> int:
    """Return button height based on density, with optional user override from settings."""
    default = 25 if density == "compact" else 30
    try:
        h = int(load_settings().get("btn_height", default))
        return h if 24 <= h <= 56 else default
    except Exception:
        return default


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
    
    # 1. Button height (the only working dynamic replacement in the QSS)
    qss = qss.replace("{{BUTTON_HEIGHT}}", str(density_button_height(density)))
    
    # 2. Custom Primary Accent Color (Orange theme color replacement)
    accent_color = settings.get("accent_color", "#E55B3C")
    hover_color = _adjust_hex_color(accent_color, -20)
    pressed_color = _adjust_hex_color(accent_color, -40)
    
    qss = qss.replace("#E55B3C", accent_color)
    qss = qss.replace("#CC4E30", hover_color)
    qss = qss.replace("#B23F23", pressed_color)
    
    # 3. Custom Window Backgrounds
    custom_bg = settings.get("app_bg_color", "")
    custom_sidebar = settings.get("sidebar_bg_color", "")
    custom_card = settings.get("card_bg_color", "")
    
    if theme == "light":
        if custom_bg:
            qss = qss.replace("#F3F3F3", custom_bg)
        if custom_sidebar:
            qss = qss.replace("#F9F9F9", custom_sidebar)
        if custom_card:
            qss = qss.replace("#FFFFFF", custom_card)
    else:  # dark theme — app bg and sidebar share #202020 token; one replacement covers both
        if custom_bg or custom_sidebar:
            qss = qss.replace("#202020", custom_bg or custom_sidebar)
        if custom_card:
            qss = qss.replace("#2C2C2C", custom_card)
            
    # 4. Custom Border Radius
    card_radius = settings.get("card_radius", 8)
    btn_radius = settings.get("btn_radius", 4)
    qss = qss.replace("border-radius: 8px;", f"border-radius: {card_radius}px;")
    qss = qss.replace("border-radius: 6px;", f"border-radius: {max(2, card_radius - 2)}px;")
    qss = qss.replace("border-radius: 4px;", f"border-radius: {btn_radius}px;")
    
    # 5. Custom Font Size
    base_font_size = settings.get("base_font_size", 14)
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


def set_status(widget, status: str):
    """Apply a status property and repolish. Used for both frames and badges."""
    widget.setProperty("status", status)
    repolish(widget)


# Aliases kept for backwards compatibility with existing tab code
set_status_frame = set_status
set_status_badge = set_status


FLUENT_GLYPHS = {
    "nginx":      "",  # Globe
    "phpmyadmin": "",  # Library/Storage (MDL2 — Win10 safe)
    "php":        "",  # Code
    "dashboard":  "",  # Home
    "running":    "",  # CheckMark
    "stopped":    "",  # Cancel
    "partial":    "",  # Warning
}
