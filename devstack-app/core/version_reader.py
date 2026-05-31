import subprocess
import time
from pathlib import Path

from core.config import load_settings


_VERSION_CACHE = {}
_CACHE_TTL_SECONDS = 60


def _run_version_cmd(exe_path: str, args: list) -> str:
    try:
        result = subprocess.run(
            [exe_path] + args,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            ),
        )
        output = (result.stdout or result.stderr or "").strip()
        return output.split("\n")[0] if output else ""
    except Exception:
        return ""


def get_php_version(bin_dir: str) -> str:
    php = Path(bin_dir) / "php.exe"
    if php.exists():
        out = _run_version_cmd(str(php), ["--version"])
        if out.startswith("PHP"):
            return out.split("(")[0].strip()
    return ""


def get_nginx_version(bin_dir: str) -> str:
    nginx = Path(bin_dir) / "nginx.exe"
    if nginx.exists():
        out = _run_version_cmd(str(nginx), ["-v"])
        if "nginx/" in out:
            return out.split("nginx/")[-1].split()[0]
    return ""


def get_mysql_version(bin_dir: str) -> str:
    mysql = Path(bin_dir) / "mysql.exe"
    if mysql.exists():
        out = _run_version_cmd(str(mysql), ["--version"])
        if out:
            parts = out.strip().split()
            for p in parts:
                if p and p[0].isdigit():
                    return p.strip(",")
    return ""


def get_all_versions(stack_root: str) -> dict:
    settings = load_settings()
    active_php_folder = settings.get("active_php_folder", "php")
    active_php_dir = Path(stack_root) / active_php_folder
    if not active_php_dir.exists():
        active_php_dir = Path(stack_root) / "php"

    cache_key = f"{stack_root}|{active_php_dir}"
    now = time.time()
    cached = _VERSION_CACHE.get(cache_key)
    if cached and now - cached["timestamp"] < _CACHE_TTL_SECONDS:
        return cached["versions"].copy()

    versions = {
        "php": get_php_version(str(active_php_dir)),
        "nginx": get_nginx_version(str(Path(stack_root) / "nginx")),
        "mysql": get_mysql_version(str(Path(stack_root) / "mysql" / "bin")),
    }
    _VERSION_CACHE[cache_key] = {"timestamp": now, "versions": versions}
    return versions.copy()
