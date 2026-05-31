import json
import subprocess
from pathlib import Path


def get_status(stack_root: str) -> dict:
    from core.config import load_settings
    s = load_settings()
    ports = {
        "nginx":  int(s.get("nginx_port",  80)),
        "php":    int(s.get("php_port",    9000)),
        "mysql":  int(s.get("mysql_port",  3306)),
    }

    ps_path = Path(stack_root) / "tools" / "status.ps1"
    if not ps_path.exists():
        return _fallback_status(ports)

    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(ps_path),
        "-nginxPort",  str(ports["nginx"]),
        "-phpPort",    str(ports["php"]),
        "-mysqlPort",  str(ports["mysql"]),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            ),
        )
        if result.returncode == 0 and result.stdout.strip():
            return _normalize(json.loads(result.stdout.strip()))
    except Exception:
        pass
    return _fallback_status(ports)


def _fallback_status(ports: dict) -> dict:
    """Return a fully-stopped status using already-loaded port values."""
    names = {"nginx": "Nginx", "php": "PHP FastCGI", "mysql": "MariaDB"}
    return {
        "generated_at": "",
        "machine": "",
        "overall": "stopped",
        "services": [
            {
                "key": key, "name": names[key], "process": key,
                "port": ports[key],
                "process_running": False, "port_listening": False, "state": "stopped",
            }
            for key in ("nginx", "php", "mysql")
        ],
    }


def _normalize(data: dict) -> dict:
    service_states = []
    for svc in data.get("services", []):
        proc = svc.get("process_running", False)
        port = svc.get("port_listening",  False)
        state = "running" if proc and port else "partial" if proc or port else "stopped"
        service_states.append({
            "key":             svc.get("key", ""),
            "name":            svc.get("name", ""),
            "process":         svc.get("process", ""),
            "port":            svc.get("port", 0),
            "process_running": proc,
            "port_listening":  port,
            "state":           state,
        })
    running = sum(1 for s in service_states if s["state"] == "running")
    partial = sum(1 for s in service_states if s["state"] == "partial")
    overall = "running" if running == len(service_states) else "partial" if running or partial else "stopped"
    return {
        "generated_at": data.get("generated_at", ""),
        "machine":       data.get("machine", ""),
        "services":      service_states,
        "overall":       overall,
    }
