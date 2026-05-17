import json
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR = APP_DIR / "config"

_config_dir = Path(os.environ.get("DEVSTACK_CONFIG_DIR", str(DEFAULT_CONFIG_DIR)))

_config_dir.mkdir(parents=True, exist_ok=True)

APP_SETTINGS_PATH = _config_dir / "app-settings.json"
APP_SITES_PATH = _config_dir / "sites.json"


def load_sites() -> list:
    if APP_SITES_PATH.exists():
        try:
            return json.loads(APP_SITES_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_site(site: dict) -> None:
    sites = load_sites()
    for i, s in enumerate(sites):
        if s.get("folder") == site.get("folder"):
            sites[i] = site
            break
    else:
        sites.append(site)
    APP_SITES_PATH.write_text(
        json.dumps(sites, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def delete_site(folder: str) -> None:
    sites = load_sites()
    sites = [s for s in sites if s.get("folder") != folder]
    APP_SITES_PATH.write_text(
        json.dumps(sites, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _resolve(path: str) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = (APP_DIR / p).resolve()
    return str(p)


def find_stack_root() -> str:
    candidates = [
        str(APP_DIR.parent / "devstack-template"),
        str(APP_DIR / ".." / "devstack-template"),
        "C:\\portable-stack",
        "D:\\portable-stack",
    ]
    for p in candidates:
        if (Path(p) / "tools" / "control.ps1").exists():
            return str(Path(p).resolve())
    return _resolve("../devstack-template")


DEFAULT_SETTINGS = {
    "stack_root": find_stack_root(),
    "apache_port": 8088,
    "nginx_port": 80,
    "php_port": 9000,
    "mysql_port": 3306,
    "auto_refresh_interval": 5,
    "php_timezone": "UTC",
    "start_with_windows": False,
    "ui_density": "comfortable",
    "theme": "light",
}


def load_settings() -> dict:
    if APP_SETTINGS_PATH.exists():
        try:
            data = json.loads(APP_SETTINGS_PATH.read_text(encoding="utf-8"))
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            merged["stack_root"] = _resolve(merged["stack_root"])
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    merged = DEFAULT_SETTINGS.copy()
    merged.update(settings)
    merged["stack_root"] = _resolve(merged["stack_root"])
    APP_SETTINGS_PATH.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )
