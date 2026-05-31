from pathlib import Path

LOG_PATHS_FLAT = {
    "nginx_error": ("Nginx Error", ["nginx/logs/error.log"]),
    "nginx_access": ("Nginx Access", ["nginx/logs/access.log"]),
    "mysql_error": ("MariaDB Error", ["mysql/data/*.err"]),
}


def tail_file(path: Path, n: int = 100) -> str:
    if not path.exists():
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except Exception as e:
        return f"Error reading log: {e}"


def _resolve_glob(base: Path, pattern: str) -> list[Path]:
    return list(base.glob(pattern))


def get_log(stack_root: str, log_key: str, n: int = 100) -> str:
    info = LOG_PATHS_FLAT.get(log_key)
    if not info:
        return ""
    base = Path(stack_root)
    parts = []
    for pattern in info[1]:
        found = _resolve_glob(base, pattern)
        for f in found:
            parts.append(tail_file(f, n))
    return "\n".join(parts).strip()


def get_log_sources() -> list[dict]:
    return [
        {"key": k, "name": v[0]} for k, v in LOG_PATHS_FLAT.items()
    ]
