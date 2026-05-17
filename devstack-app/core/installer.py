import os
import subprocess
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from core.version_reader import get_php_version

class InstallWorker(QThread):
    progress = Signal(str, int)  # (Status Message, Percentage)
    log_emitted = Signal(str)    # (Detailed Log Line)
    finished = Signal(bool, str) # (Success, Message)

    def __init__(self, plugin, stack_root: str, params: dict, php_folder: str, db_port: int = 3306):
        super().__init__()
        self.plugin = plugin
        self.stack_root = Path(stack_root)
        self.params = params
        self.php_folder = php_folder
        self.db_port = db_port

    def run(self):
        try:
            # 1. Prepare target directory in htdocs
            site_folder_name = self.params.get("site_name", "dev_site").strip()
            target_dir = self.stack_root / "htdocs" / site_folder_name
            
            # Ensure folder name is valid and doesn't overwrite core assets
            if not site_folder_name or site_folder_name in ["dashboard", "assets"]:
                self.finished.emit(False, "Invalid site folder name.")
                return

            self.progress.emit("Initializing environment...", 5)
            self.log_emitted.emit(">>> Starting One-Click Installation Process")
            self.log_emitted.emit(f"Site Target Directory: htdocs/{site_folder_name}")

            # Extract custom host & port if provided
            db_host = self.params.get("db_host", "127.0.0.1").strip()
            db_port_str = self.params.get("db_port", "").strip()
            db_port = int(db_port_str) if db_port_str.isdigit() else self.db_port

            self.log_emitted.emit(f"Database Config: Host={db_host}, Port={db_port}")

            # 2. Setup mock database connection object that executes via local mysql.exe CLI
            class SubprocessSQLConnection:
                def __init__(self, stack_root, db_host, db_port, log_signal):
                    self.stack_root = stack_root
                    self.db_host = db_host
                    self.db_port = db_port
                    self.log_signal = log_signal

                def cursor(self):
                    return self

                def execute(self, query):
                    mysql_exe = self.stack_root / "mysql" / "bin" / "mysql.exe"
                    if not mysql_exe.exists():
                        raise FileNotFoundError("mysql.exe not found in stack.")
                    
                    self.log_signal.emit(f"Executing SQL Query: {query}")
                    cmd = [
                        str(mysql_exe),
                        "-h", self.db_host,
                        "-P", str(self.db_port),
                        "-u", "root",
                        "-e", query
                    ]
                    
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        creationflags=(subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0),
                        timeout=15
                    )
                    if res.returncode != 0:
                        raise Exception(f"MariaDB Error: {res.stderr or res.stdout}")
                    self.log_signal.emit("SQL Query executed successfully.")

                def close(self):
                    pass

            mysql_conn = SubprocessSQLConnection(self.stack_root, db_host, db_port, self.log_emitted)

            # 3. Call the plugin's install routine with our dynamic logging hook
            def log_callback(msg):
                self.log_emitted.emit(msg)

            self.plugin.install(target_dir, self.params, mysql_conn, self.emit_progress, log_callback)

            # 4. If a custom PHP folder is selected, write directory FPM mapping inside a local .htaccess file!
            self.setup_php_routing(target_dir)

            self.finished.emit(True, f"Successfully installed {self.plugin.meta['name']} into htdocs/{site_folder_name}!")
        except Exception as e:
            self.log_emitted.emit(f"FATAL ERROR: {str(e)}")
            self.finished.emit(False, str(e))

    def emit_progress(self, message, percent):
        self.progress.emit(message, percent)

    def setup_php_routing(self, target_dir: Path):
        """Sets up custom PHP-FPM fastcgi port mappings in target .htaccess if needed"""
        if not self.php_folder or self.php_folder == "php":
            return # Runs on stack's default global PHP FPM port (9000)
            
        # Discover FPM port mapping based on php folder suffix (e.g. php74 -> 9074, php81 -> 9081)
        # Suffix matching is the standard developer convention!
        port = 9000
        suffix = self.php_folder.replace("php", "").strip()
        if suffix.isdigit():
            port = 9000 + int(suffix)
            
        htaccess_path = target_dir / ".htaccess"
        htaccess_content = ""
        
        if htaccess_path.exists():
            htaccess_content = htaccess_path.read_text(encoding="utf-8") + "\n\n"
            
        routing_block = f"""# DevStack Directory PHP-FPM Version Selector Mapping
<FilesMatch \\.php$>
    SetHandler "proxy:fcgi://127.0.0.1:{port}"
</FilesMatch>"""

        htaccess_path.write_text(htaccess_content + routing_block, encoding="utf-8")


def discover_php_versions(stack_root: str) -> list:
    """Discovers all php folders in the stack root (e.g. php, php74, php81) and returns their versions"""
    php_list = []
    root = Path(stack_root)
    if not root.exists():
        return php_list
        
    for p in root.iterdir():
        if p.is_dir() and p.name.startswith("php"):
            version_str = get_php_version(str(p))
            if version_str:
                php_list.append({
                    "folder": p.name,
                    "version": version_str
                })
                
    # Fallback to default if list is empty
    if not php_list:
        default_dir = root / "php"
        if default_dir.exists():
            php_list.append({
                "folder": "php",
                "version": "PHP 8.2 (Default)"
            })
            
    return php_list
