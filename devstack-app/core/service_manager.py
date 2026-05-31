import subprocess
import time
import re
from pathlib import Path

from core.utils import no_window_flags as _flags

SERVICES = {
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
        "args": ["--defaults-file={root}/mysql/my.ini", "--init-file={root}/mysql/devstack-grants.sql"],
        "wd": "{root}/mysql/bin",
    },
}

# Order services start in: database first, then PHP, then the web server.
START_ORDER = ["mysql", "php", "nginx"]


def _resolve(root: str, template: str) -> str:
    return template.replace("{root}", root.replace("\\", "/"))


def _is_running(exe_name: str) -> bool:
    try:
        r = subprocess.run(
            ["tasklist", "/nh", "/fi", f"imagename eq {exe_name}"],
            capture_output=True, text=True, timeout=3,
            creationflags=_flags(),
        )
        return exe_name.lower() in r.stdout.lower()
    except Exception:
        return False


def _kill(exe_name: str) -> None:
    for _ in range(3):
        try:
            subprocess.run(
                ["taskkill", "/f", "/t", "/im", exe_name],
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


def _find_port_user(port: int) -> str:
    """Return 'ProcessName (PID X)' that holds the given TCP port, or empty string."""
    try:
        r = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
            creationflags=_flags(),
        )
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and f":{port}" in parts[1] and "LISTENING" in parts[3]:
                pid = parts[4]
                r2 = subprocess.run(
                    ["tasklist", "/fi", f"PID eq {pid}", "/nh", "/fo", "CSV"],
                    capture_output=True, text=True, timeout=3,
                    creationflags=_flags(),
                )
                out = r2.stdout.strip()
                if out and "No tasks" not in out:
                    name = out.split(",")[0].strip('"')
                    return f"{name} (PID {pid})"
    except Exception:
        pass
    return ""


def _sync_nginx_config(stack_root: str, nginx_port: int, client_max_body_size: str) -> str | None:
    nginx_conf = Path(stack_root) / "nginx" / "conf" / "nginx.conf"
    if not nginx_conf.exists():
        return None
    try:
        content = nginx_conf.read_text(encoding="utf-8")
        escaped_root = stack_root.replace("\\", "/")
        content = re.sub(r'\blisten\s+\d+;', f'listen       {nginx_port};', content)
        content = re.sub(
            r'^\s*#?\s*root\s+[^\n;]+htdocs;',
            f'        root   {escaped_root}/htdocs;',
            content, flags=re.MULTILINE,
        )

        size = (client_max_body_size or "128M").strip()
        if re.search(r'\bclient_max_body_size\s+[^;]+;', content):
            content = re.sub(r'\bclient_max_body_size\s+[^;]+;', f'client_max_body_size {size};', content)
        else:
            content = re.sub(
                r'(default_type\s+application/octet-stream;)',
                r'\1\n\n    client_max_body_size ' + size + ';',
                content, count=1,
            )
        nginx_conf.write_text(content, encoding="utf-8")
        return None
    except Exception as e:
        return f"Nginx config sync failed: {e}"


def _sync_mysql_config(stack_root: str, mysql_port: int) -> str | None:
    my_ini = Path(stack_root) / "mysql" / "my.ini"
    if not my_ini.exists():
        return None
    try:
        content = my_ini.read_text(encoding="utf-8")
        escaped_root = stack_root.replace("\\", "/")
        content = re.sub(r'basedir\s*=\s*[^\n\r]+', f'basedir = "{escaped_root}/mysql"', content)
        content = re.sub(r'datadir\s*=\s*[^\n\r]+', f'datadir = "{escaped_root}/mysql/data"', content)
        content = re.sub(r'\bport\s*=\s*\d+', f'port = {mysql_port}', content)
        my_ini.write_text(content, encoding="utf-8")
        return None
    except Exception as e:
        return f"MySQL config sync failed: {e}"


def start(stack_root: str, service: str = "all") -> dict:
    from core.config import load_settings
    settings = load_settings()
    nginx_port = int(settings.get("nginx_port", 80))
    php_port = int(settings.get("php_port", 9000))
    mysql_port = int(settings.get("mysql_port", 3306))
    nginx_client_max_body_size = settings.get("nginx_client_max_body_size", "128M")

    SERVICES["nginx"]["port"] = nginx_port
    SERVICES["php"]["port"] = php_port
    SERVICES["mysql"]["port"] = mysql_port
    SERVICES["mysql"]["args"] = [
        "--defaults-file={root}/mysql/my.ini",
        f"--port={mysql_port}",
        "--init-file={root}/mysql/devstack-grants.sql",
    ]

    active_php = settings.get("active_php_folder", "php")
    SERVICES["php"]["exe"] = f"{active_php}/php-cgi.exe"
    SERVICES["php"]["args"] = ["-b", f"127.0.0.1:{php_port}", "-c", f"{{root}}/{active_php}/php.ini"]
    SERVICES["php"]["wd"] = f"{{root}}/{active_php}"

    # Sync configs to disk (corrects portable paths + ports) before starting
    sync_errors = [e for e in (
        _sync_nginx_config(stack_root, nginx_port, nginx_client_max_body_size),
        _sync_mysql_config(stack_root, mysql_port),
    ) if e]
    if sync_errors:
        return {"success": False, "error": "; ".join(sync_errors)}

    keys = START_ORDER if service == "all" else [service]

    for k in keys:
        if k not in SERVICES:
            return {"success": False, "error": f"Unknown service: {k}"}
        _kill(SERVICES[k]["process"])

    time.sleep(1)

    started = []
    errors = []
    for k in keys:
        svc = SERVICES[k]
        # exe paths are relative to stack_root (no {root} placeholder), so prepend it
        exe = Path(stack_root) / _resolve(stack_root, svc["exe"])
        if not exe.exists():
            errors.append(f"{svc['name']} binary not found: {exe}")
            continue
        args = [_resolve(stack_root, a) for a in svc["args"]]
        wd = _resolve(stack_root, svc["wd"])
        try:
            flags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                flags |= subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB"):
                flags |= subprocess.CREATE_BREAKAWAY_FROM_JOB

            # php-cgi: PHP_FCGI_CHILDREN is ignored on Windows — spawn 3 independent
            # php-cgi processes on the same port so one crash doesn't take PHP down.
            env = None
            if k == "php":
                import os as _os
                env = _os.environ.copy()
                env["PHP_FCGI_MAX_REQUESTS"] = "0"

            spawn_count = 3 if k == "php" else 1
            last_p = None
            for _ in range(spawn_count):
                try:
                    last_p = subprocess.Popen([str(exe)] + args, cwd=wd, creationflags=flags, env=env)
                except PermissionError:
                    fallback = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                    last_p = subprocess.Popen([str(exe)] + args, cwd=wd, creationflags=fallback, env=env)
            started.append((k, svc, last_p))
        except Exception as e:
            errors.append(f"{svc['name']}: {e}")

    timeouts = {"mysql": 15, "php": 8, "nginx": 5}
    for k, svc, p in started:
        if not _wait_for(svc["process"], timeouts.get(k, 8)):
            port_user = _find_port_user(svc["port"])
            if port_user:
                errors.append(
                    f"{svc['name']} failed to start — port {svc['port']} is already in use by "
                    f"{port_user}. Stop that process or change the port in Settings."
                )
            else:
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
        names = [svc["process"] for svc in SERVICES.values()]
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
