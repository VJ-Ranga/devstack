import subprocess
import time
from pathlib import Path

SERVICES = {
    "apache": {
        "name": "Apache", "process": "httpd.exe", "port": 8088,
        "exe": "apache/bin/httpd.exe",
        "args": ["-d", "{root}/apache"],
        "wd": "{root}/apache/bin",
    },
    "nginx": {
        "name": "Nginx", "process": "nginx.exe", "port": 80,
        "exe": "nginx/nginx.exe",
        "args": ["-p", "{root}/nginx"],
        "wd": "{root}/nginx",
    },
    "php": {
        "name": "PHP FastCGI", "process": "php-cgi.exe", "port": 9000,
        "exe": "php/php-cgi.exe",
        "args": ["-b", "127.0.0.1:9000", "-c", "{root}/php/php.ini"],
        "wd": "{root}/php",
    },
    "mysql": {
        "name": "MariaDB", "process": "mysqld.exe", "port": 3306,
        "exe": "mysql/bin/mysqld.exe",
        "args": ["--defaults-file={root}/mysql/my.ini", "--skip-name-resolve"],
        "wd": "{root}/mysql/bin",
    },
}


def _flags():
    f = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        f |= subprocess.CREATE_NO_WINDOW
    return f


def _resolve(root: str, template: str) -> str:
    return template.replace("{root}", root.replace("\\", "/"))


def _is_running(exe_name: str) -> bool:
    name = exe_name.replace(".exe", "")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"if (Get-Process -Name '{name}' -ErrorAction SilentlyContinue) {{ '1' }}"],
            capture_output=True, text=True, timeout=5,
            creationflags=_flags(),
        )
        return r.stdout.strip() == "1"
    except Exception:
        return False


def _kill(exe_name: str) -> None:
    for _ in range(3):
        try:
            subprocess.run(
                ["taskkill", "/f", "/im", exe_name],
                capture_output=True, timeout=5, creationflags=_flags(),
            )
        except Exception:
            pass
        if not _is_running(exe_name):
            return
        time.sleep(1)


def _wait_for(name: str, timeout: int) -> bool:
    for _ in range(timeout):
        if _is_running(name):
            return True
        time.sleep(1)
    return False


def start(stack_root: str, service: str = "all") -> dict:
    from core.config import load_settings
    settings = load_settings()
    apache_port = int(settings.get("apache_port", 8088))
    nginx_port = int(settings.get("nginx_port", 80))
    php_port = int(settings.get("php_port", 9000))
    mysql_port = int(settings.get("mysql_port", 3306))

    SERVICES["apache"]["port"] = apache_port
    SERVICES["nginx"]["port"] = nginx_port
    SERVICES["php"]["port"] = php_port
    SERVICES["mysql"]["port"] = mysql_port
    SERVICES["mysql"]["args"] = ["--defaults-file={root}/mysql/my.ini", f"--port={mysql_port}", "--skip-name-resolve", "--skip-grant-tables"]

    active_php = settings.get("active_php_folder", "php")
    SERVICES["php"]["exe"] = f"{active_php}/php-cgi.exe"
    SERVICES["php"]["args"] = ["-b", f"127.0.0.1:{php_port}", "-c", f"{{root}}/{active_php}/php.ini"]
    SERVICES["php"]["wd"] = f"{{root}}/{active_php}"

    if service == "all":
        keys = ["mysql", "php", "apache", "nginx"]
    else:
        keys = [service]

    for k in keys:
        svc = SERVICES.get(k)
        if not svc:
            return {"success": False, "error": f"Unknown service: {k}"}
        _kill(svc["process"])

    time.sleep(1)

    started = []
    errors = []
    for k in keys:
        svc = SERVICES[k]
        exe = Path(stack_root) / _resolve(stack_root, svc["exe"])
        if not exe.exists():
            errors.append(f"{svc['name']} binary not found: {exe}")
            continue
        args = [_resolve(stack_root, a) for a in svc["args"]]
        wd = _resolve(stack_root, svc["wd"])
        try:
            # Try to start the service with job breakaway so it persists if the manager closes
            flags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                flags |= subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB"):
                flags |= subprocess.CREATE_BREAKAWAY_FROM_JOB
            try:
                p = subprocess.Popen(
                    [str(exe)] + args,
                    cwd=wd,
                    creationflags=flags,
                )
            except PermissionError:
                # Fallback to starting without breakaway if restricted by the parent job
                flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                p = subprocess.Popen(
                    [str(exe)] + args,
                    cwd=wd,
                    creationflags=flags,
                )
            started.append((k, svc, p))
        except Exception as e:
            errors.append(f"{svc['name']}: {e}")

    timeouts = {"mysql": 15, "php": 8, "apache": 8, "nginx": 5}
    for k, svc, p in started:
        timeout = timeouts.get(k, 8)
        if not _wait_for(svc["process"], timeout):
            errors.append(f"{svc['name']} failed to start. Check port {svc['port']} for conflicts.")
            try:
                p.kill()
            except Exception:
                pass

    if errors:
        return {"success": False, "error": "; ".join(errors), "partial": True}
    return {"success": True}


def stop(stack_root: str, service: str = "all") -> dict:
    if service == "all":
        names = [svc["process"] for svc in SERVICES.values() if svc.get("process")]
    else:
        svc = SERVICES.get(service)
        if not svc:
            return {"success": False, "error": f"Unknown service: {service}"}
        names = [svc["process"]]
    for name in names:
        _kill(name)
    return {"success": True}


def restart(stack_root: str, service: str = "all") -> dict:
    stop(stack_root, service)
    time.sleep(1)
    return start(stack_root, service)
