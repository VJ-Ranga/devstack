import subprocess
from pathlib import Path

from core.utils import no_window_flags
from core.version_reader import get_php_version


class SubprocessSQLConnection:
    def __init__(self, stack_root, db_host, db_port, log_signal=None):
        self.stack_root = Path(stack_root)
        self.db_host = db_host
        self.db_port = db_port
        self.log_signal = log_signal

    def cursor(self):
        return self

    def execute(self, query):
        mysql_exe = self.stack_root / "mysql" / "bin" / "mysql.exe"
        if not mysql_exe.exists():
            raise FileNotFoundError("mysql.exe not found in stack.")

        if self.log_signal:
            if hasattr(self.log_signal, "emit"):
                self.log_signal.emit(f"Executing SQL Query: {query}")
            else:
                self.log_signal(f"Executing SQL Query: {query}")

        cmd = [
            str(mysql_exe),
            f"--host={self.db_host}",
            f"--port={self.db_port}",
            "--ssl=0",
            "-u",
            "root",
            "-e",
            query,
        ]

        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=no_window_flags(),
            timeout=15,
        )
        if res.returncode != 0:
            raise Exception(f"MariaDB Error: {res.stderr or res.stdout}")

    def close(self):
        pass


def get_mysql_connection(stack_root: str, db_port: int = 3306) -> SubprocessSQLConnection:
    return SubprocessSQLConnection(Path(stack_root), "127.0.0.1", db_port)


def discover_php_versions(stack_root: str) -> list:
    php_list = []
    root = Path(stack_root)
    if not root.exists():
        return php_list

    for p in root.iterdir():
        if p.is_dir() and p.name.startswith("php"):
            version_str = get_php_version(str(p))
            if version_str:
                php_list.append({"folder": p.name, "version": version_str})

    if not php_list:
        default_dir = root / "php"
        if default_dir.exists():
            php_list.append({"folder": "php", "version": "PHP 8.2 (Default)"})

    return php_list
