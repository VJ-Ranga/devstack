import subprocess
import time
import re
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
        "args": ["--defaults-file={root}/mysql/my.ini", "--init-file={root}/mysql/devstack-grants.sql"],
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


def _stop_apache_graceful(stack_root: str) -> None:
    httpd = Path(stack_root) / "apache" / "bin" / "httpd.exe"
    if not httpd.exists():
        return
    try:
        subprocess.run(
            [str(httpd), "-k", "shutdown", "-d", str(Path(stack_root) / "apache")],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=_flags(),
        )
    except Exception:
        pass
    for _ in range(8):
        if not _is_running("httpd.exe"):
            return
        time.sleep(0.5)


def _wait_for(name: str, timeout: int) -> bool:
    for _ in range(timeout):
        if _is_running(name):
            return True
        time.sleep(1)
    return False


def _sync_nginx_config(stack_root: str, nginx_port: int) -> None:
    nginx_conf = Path(stack_root) / "nginx" / "conf" / "nginx.conf"
    if not nginx_conf.exists():
        return
    try:
        content = nginx_conf.read_text(encoding="utf-8")
        escaped_root = stack_root.replace("\\", "/")
        content = re.sub(r'\blisten\s+\d+;', f'listen       {nginx_port};', content)
        content = re.sub(r'\broot\s+[^;]+htdocs;', f'root   {escaped_root}/htdocs;', content)
        nginx_conf.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"Error syncing Nginx config: {e}")


def _sync_apache_config(stack_root: str, apache_port: int, active_php: str) -> None:
    httpd_conf = Path(stack_root) / "apache" / "conf" / "httpd.conf"
    if not httpd_conf.exists():
        return
    try:
        content = httpd_conf.read_text(encoding="utf-8")
        escaped_root = stack_root.replace("\\", "/")
        content = re.sub(r'\bListen\s+\d+', f'Listen {apache_port}', content)
        content = re.sub(r'\bServerName\s+localhost:\d+', f'ServerName localhost:{apache_port}', content)
        content = re.sub(r'Define\s+SRVROOT\s+"[^"]+"', f'Define SRVROOT "{escaped_root}/apache"', content)
        content = re.sub(r'DocumentRoot\s+"[^"]+"', f'DocumentRoot "{escaped_root}/htdocs"', content)
        content = re.sub(r'<Directory\s+"[^"]+htdocs">', f'<Directory "{escaped_root}/htdocs">', content)
        
        dll_name = "php8apache2_4.dll"
        module_name = "php_module"
        if "php7" in active_php:
            dll_name = "php7apache2_4.dll"
            module_name = "php7_module"
        elif "php8" in active_php or active_php == "php":
            dll_name = "php8apache2_4.dll"
            module_name = "php_module"
            
        dll_path = f"{escaped_root}/{active_php}/{dll_name}"
        
        content = re.sub(r'LoadModule\s+php\d?_module\s+"[^"]+"', f'LoadModule {module_name} "{dll_path}"', content)
        content = re.sub(r'PHPIniDir\s+"[^"]+"', f'PHPIniDir "{escaped_root}/{active_php}"', content)
        
        httpd_conf.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"Error syncing Apache config: {e}")


def _sync_mysql_config(stack_root: str, mysql_port: int) -> None:
    my_ini = Path(stack_root) / "mysql" / "my.ini"
    if not my_ini.exists():
        return
    try:
        content = my_ini.read_text(encoding="utf-8")
        escaped_root = stack_root.replace("\\", "/")
        content = re.sub(r'basedir\s*=\s*[^\n\r]+', f'basedir = "{escaped_root}/mysql"', content)
        content = re.sub(r'datadir\s*=\s*[^\n\r]+', f'datadir = "{escaped_root}/mysql/data"', content)
        content = re.sub(r'\bport\s*=\s*\d+', f'port = {mysql_port}', content)
        my_ini.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"Error syncing MySQL config: {e}")


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
    SERVICES["mysql"]["args"] = [
        "--defaults-file={root}/mysql/my.ini",
        f"--port={mysql_port}",
        "--init-file={root}/mysql/devstack-grants.sql",
    ]

    active_php = settings.get("active_php_folder", "php")
    SERVICES["php"]["exe"] = f"{active_php}/php-cgi.exe"
    SERVICES["php"]["args"] = ["-b", f"127.0.0.1:{php_port}", "-c", f"{{root}}/{active_php}/php.ini"]
    SERVICES["php"]["wd"] = f"{{root}}/{active_php}"

    # Dynamically auto-sync web servers and database absolute paths and port bindings on disk
    _sync_nginx_config(stack_root, nginx_port)
    _sync_apache_config(stack_root, apache_port, active_php)
    _sync_mysql_config(stack_root, mysql_port)

    if service == "all":
        keys = ["mysql", "php", "apache", "nginx"]
    else:
        keys = [service]

    for k in keys:
        svc = SERVICES.get(k)
        if not svc:
            return {"success": False, "error": f"Unknown service: {k}"}
        if k == "apache":
            _stop_apache_graceful(stack_root)
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
        if name.lower() == "httpd.exe":
            _stop_apache_graceful(stack_root)
        _kill(name)
    return {"success": True}


def restart(stack_root: str, service: str = "all") -> dict:
    stop(stack_root, service)
    time.sleep(1)
    return start(stack_root, service)
