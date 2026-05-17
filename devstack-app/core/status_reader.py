import json
import subprocess
from pathlib import Path


def get_status(stack_root: str) -> dict:
    from core.config import load_settings
    settings = load_settings()
    apache_port = int(settings.get("apache_port", 8088))
    nginx_port = int(settings.get("nginx_port", 80))
    php_port = int(settings.get("php_port", 9000))
    mysql_port = int(settings.get("mysql_port", 3306))

    ps_path = Path(stack_root) / "tools" / "status.ps1"
    if not ps_path.exists():
        return _fallback_status(stack_root)
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(ps_path),
        "-apachePort", str(apache_port),
        "-nginxPort", str(nginx_port),
        "-phpPort", str(php_port),
        "-mysqlPort", str(mysql_port),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            ),
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return _normalize(data, stack_root)
        return _fallback_status(stack_root)
    except Exception:
        return _fallback_status(stack_root)


def _fallback_status(stack_root: str) -> dict:
    from core.config import load_settings
    settings = load_settings()
    apache_port = int(settings.get("apache_port", 8088))
    nginx_port = int(settings.get("nginx_port", 80))
    php_port = int(settings.get("php_port", 9000))
    mysql_port = int(settings.get("mysql_port", 3306))

    services = []
    for key in ("apache", "nginx", "php", "mysql"):
        services.append({
            "key": key,
            "name": {"apache": "Apache", "nginx": "Nginx", "php": "PHP FastCGI", "mysql": "MariaDB"}[key],
            "process": key,
            "port": {"apache": apache_port, "nginx": nginx_port, "php": php_port, "mysql": mysql_port}[key],
            "process_running": False,
            "port_listening": False,
            "state": "stopped",
        })
    return {
        "generated_at": "",
        "machine": "",
        "services": services,
        "overall": "stopped",
    }


def _normalize(data: dict, stack_root: str) -> dict:
    raw_services = data.get("services", [])
    service_states = []
    for svc in raw_services:
        proc = svc.get("process_running", False)
        port = svc.get("port_listening", False)
        if proc and port:
            state = "running"
        elif proc or port:
            state = "partial"
        else:
            state = "stopped"
        service_states.append({
            "key": svc.get("key", ""),
            "name": svc.get("name", ""),
            "process": svc.get("process", ""),
            "port": svc.get("port", 0),
            "process_running": proc,
            "port_listening": port,
            "state": state,
        })
    running_count = sum(1 for s in service_states if s["state"] == "running")
    partial_count = sum(1 for s in service_states if s["state"] == "partial")
    if running_count == len(service_states):
        overall = "running"
    elif running_count > 0 or partial_count > 0:
        overall = "partial"
    else:
        overall = "stopped"
    return {
        "generated_at": data.get("generated_at", ""),
        "machine": data.get("machine", ""),
        "services": service_states,
        "overall": overall,
    }
