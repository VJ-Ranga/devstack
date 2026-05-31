#!/usr/bin/env python3
"""
DevStack MCP Server

Exposes DevStack stack management and development tools to AI coding agents.
Compatible with Claude Code, OpenCode, Cursor Agent, and any MCP-compatible client.

Transport: stdio (runs as a local subprocess — no network config needed)
Usage:     python devstack-mcp/server.py
"""

import json
import subprocess
import sys
from pathlib import Path
import shlex

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict

# ── Path setup — import DevStack core modules ──────────────────────────────────
_SERVER_DIR = Path(__file__).resolve().parent
_APP_DIR    = _SERVER_DIR.parent / "devstack-app"
sys.path.insert(0, str(_APP_DIR))

from core.config         import load_settings, load_sites       # noqa: E402
from core.status_reader  import get_status                      # noqa: E402
from core.log_reader     import get_log                         # noqa: E402
from core.service_manager import start, stop, restart           # noqa: E402
from core.utils          import no_window_flags                 # noqa: E402

# ── Server ─────────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "devstack_mcp",
    instructions=(
        "DevStack MCP gives you live access to a local Windows web stack "
        "(Apache, Nginx, PHP-CGI, MariaDB). "
        "Start with devstack_get_status to see what is running. "
        "Use devstack_read_log (nginx_error) to diagnose 502 errors. "
        "Use devstack_run_wpcli for WordPress tasks. "
        "Use devstack_run_mysql_query to inspect or modify the database. "
        "Use devstack_run_php to test PHP snippets instantly."
    ),
)

# ── Shared helpers ─────────────────────────────────────────────────────────────

def _settings() -> dict:
    return load_settings()


def _stack_root() -> str:
    return _settings()["stack_root"]


def _site_url(folder: str, app_id: str, port: int) -> str:
    base   = f"http://localhost:{port}" if port != 80 else "http://localhost"
    suffix = "public/" if app_id == "laravel" else ""
    return f"{base}/{folder}/{suffix}"


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 15) -> tuple[str, bool]:
    """Run a subprocess, return (output, success). Never raises."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd=cwd,
            creationflags=no_window_flags(),
        )
        output = ((r.stdout or "") + (r.stderr or "")).strip()
        return output or "(no output)", r.returncode == 0
    except subprocess.TimeoutExpired:
        return f"[Error] Timed out after {timeout}s.", False
    except FileNotFoundError:
        return f"[Error] Executable not found: {cmd[0]}", False
    except Exception as e:
        return f"[Error] {e}", False


def _php_exe() -> Path:
    s = _settings()
    return Path(_stack_root()) / s.get("active_php_folder", "php") / "php.exe"


def _php_ini() -> Path:
    s = _settings()
    return Path(_stack_root()) / s.get("active_php_folder", "php") / "php.ini"


def _mysql_exe() -> Path:
    return Path(_stack_root()) / "mysql" / "bin" / "mysql.exe"


def _wp_cli() -> Path:
    return Path(_stack_root()) / "tools" / "wp-cli.phar"


# ── Pydantic input models ──────────────────────────────────────────────────────

class ServiceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    service: str = Field(
        default="all",
        description='Service name: "all", "apache", "nginx", "php", or "mysql"',
        pattern=r"^(all|apache|nginx|php|mysql)$",
    )


class LogInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    service: str = Field(
        ...,
        description=(
            'Log source: "apache_error", "apache_access", '
            '"nginx_error", "nginx_access", "mysql_error"'
        ),
        pattern=r"^(apache_error|apache_access|nginx_error|nginx_access|mysql_error)$",
    )
    lines: int = Field(default=50, description="Lines to return (1–300)", ge=1, le=300)


class MySQLInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    query: str = Field(
        ...,
        description='SQL to run, e.g. "SHOW TABLES", "SELECT * FROM wp_posts LIMIT 5"',
        min_length=1,
    )
    database: str = Field(
        default="",
        description="Optional database name to USE before running the query",
    )


class CreateDBInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(
        ...,
        description="Database name — letters, numbers, underscores only",
        min_length=1, max_length=64,
        pattern=r"^[a-zA-Z0-9_]+$",
    )


class WPCLIInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    site_folder: str = Field(
        ...,
        description='htdocs subfolder name of the WP site (e.g. "myblog")',
        min_length=1,
    )
    command: str = Field(
        ...,
        description=(
            "WP-CLI command without the 'wp' prefix — "
            'e.g. "plugin list", "option get siteurl", "cache flush"'
        ),
        min_length=1,
    )

    @field_validator("site_folder")
    @classmethod
    def no_traversal(cls, v: str) -> str:
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("site_folder must be a plain folder name, not a path")
        return v


class PHPInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    code: str = Field(
        ...,
        description='PHP code to execute (with or without <?php). e.g. "echo PHP_VERSION;"',
        min_length=1,
    )
    site_folder: str = Field(
        default="",
        description="Optional: run with this site's htdocs folder as working directory",
    )


class SiteFolderInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    folder: str = Field(
        ...,
        description="htdocs subfolder name of the site (e.g. 'myblog')",
        min_length=1,
    )


# ── STATUS TOOLS ───────────────────────────────────────────────────────────────

@mcp.tool(
    name="devstack_get_status",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_get_status() -> str:
    """
    Get the current running status of all DevStack services.

    Returns process-running state, port-listening state, and overall health
    for Apache, Nginx, PHP FastCGI, and MariaDB.

    Call this first to understand the stack state before diagnosing any problem.

    Returns:
        str: JSON with keys:
             - overall (str): "running" | "partial" | "stopped"
             - services (list): each has key, name, port, process_running,
               port_listening, state
    """
    return json.dumps(get_status(_stack_root()), indent=2)


@mcp.tool(
    name="devstack_list_sites",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_list_sites() -> str:
    """
    List all websites registered in DevStack.

    Returns folder name, CMS type, PHP version, database name, and local URLs
    for every site in htdocs.

    Returns:
        str: JSON array — each item has folder, app_id, app_name, site_title,
             php_version, db_name, url, apache_url, htdocs_path.
    """
    s           = _settings()
    nginx_port  = int(s.get("nginx_port", 80))
    apache_port = int(s.get("apache_port", 8088))
    result = []
    for site in load_sites():
        folder = site.get("folder", "")
        app_id = site.get("app_id", "custom_php")
        result.append({
            **{k: v for k, v in site.items() if k != "admin_pass"},
            "url":         _site_url(folder, app_id, nginx_port),
            "apache_url":  _site_url(folder, app_id, apache_port),
            "htdocs_path": str(Path(_stack_root()) / "htdocs" / folder),
        })
    return json.dumps(result, indent=2)


@mcp.tool(
    name="devstack_get_site_info",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_get_site_info(params: SiteFolderInput) -> str:
    """
    Get full details for a specific DevStack site by its htdocs folder name.

    Useful before starting work: confirms the URL, database name, PHP version,
    and whether the folder actually exists on disk.

    Args:
        params.folder (str): htdocs subfolder name (e.g. "myblog")

    Returns:
        str: JSON with folder, app_id, url, apache_url, htdocs_path, db_name,
             php_version, php_ini_path, exists_on_disk.
             On error: JSON with "error" and "available_sites" keys.
    """
    sites = {s["folder"]: s for s in load_sites()}
    if params.folder not in sites:
        return json.dumps({
            "error":           f"Site '{params.folder}' not found.",
            "available_sites": list(sites.keys()),
            "tip":             "Use devstack_list_sites to see all registered sites.",
        })
    site        = sites[params.folder]
    s           = _settings()
    nginx_port  = int(s.get("nginx_port", 80))
    apache_port = int(s.get("apache_port", 8088))
    app_id      = site.get("app_id", "custom_php")
    site_path   = Path(_stack_root()) / "htdocs" / params.folder
    return json.dumps({
        **{k: v for k, v in site.items() if k != "admin_pass"},
        "url":          _site_url(params.folder, app_id, nginx_port),
        "apache_url":   _site_url(params.folder, app_id, apache_port),
        "htdocs_path":  str(site_path),
        "php_ini_path": str(_php_ini()),
        "exists_on_disk": site_path.exists(),
    }, indent=2)


# ── LOG TOOLS ──────────────────────────────────────────────────────────────────

@mcp.tool(
    name="devstack_read_log",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_read_log(params: LogInput) -> str:
    """
    Read recent log entries for a DevStack service.

    Tip: Start with "nginx_error" for 502/504 errors — it shows PHP crash reasons.
    Use "apache_error" for .htaccess or module issues.
    Use "mysql_error" for database startup failures.

    Args:
        params.service (str): apache_error | apache_access | nginx_error |
                              nginx_access | mysql_error
        params.lines   (int): Lines to return, default 50, max 300

    Returns:
        str: Raw log text. Returns a message if the log file doesn't exist yet.
    """
    content = get_log(_stack_root(), params.service, n=params.lines)
    if not content:
        return (
            f"No log entries found for '{params.service}'. "
            "The service may not have started, or the log file doesn't exist yet."
        )
    return content


# ── SERVICE CONTROL TOOLS ──────────────────────────────────────────────────────

@mcp.tool(
    name="devstack_start_service",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def devstack_start_service(params: ServiceInput) -> str:
    """
    Start a DevStack service. Performs a clean restart if already running.

    Args:
        params.service (str): "all" | "apache" | "nginx" | "php" | "mysql"

    Returns:
        str: JSON with success (bool) and error (str, only if failed).
    """
    return json.dumps(start(_stack_root(), params.service), indent=2)


@mcp.tool(
    name="devstack_stop_service",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False},
)
async def devstack_stop_service(params: ServiceInput) -> str:
    """
    Stop a DevStack service.

    Args:
        params.service (str): "all" | "apache" | "nginx" | "php" | "mysql"

    Returns:
        str: JSON with success (bool) and error (str, only if failed).
    """
    return json.dumps(stop(_stack_root(), params.service), indent=2)


@mcp.tool(
    name="devstack_restart_service",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def devstack_restart_service(params: ServiceInput) -> str:
    """
    Restart a DevStack service.

    Use after editing php.ini, nginx.conf, or httpd.conf for changes to take effect.

    Args:
        params.service (str): "all" | "apache" | "nginx" | "php" | "mysql"

    Returns:
        str: JSON with success (bool) and error (str, only if failed).
    """
    return json.dumps(restart(_stack_root(), params.service), indent=2)


# ── DATABASE TOOLS ─────────────────────────────────────────────────────────────

@mcp.tool(
    name="devstack_run_mysql_query",
    annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_run_mysql_query(params: MySQLInput) -> str:
    """
    Run a SQL query against the local MariaDB instance (root, no password).

    Results are returned in tabular text format for easy reading.
    Use for inspecting tables, checking data, running migrations, or resetting passwords.

    Args:
        params.query    (str): SQL to execute, e.g. "SHOW TABLES"
        params.database (str): Optional database name (e.g. "wordpress")

    Returns:
        str: Query output in tabular format, or a "[MySQL Error]" message with tips.

    Examples:
        query="SHOW DATABASES"
        query="SELECT ID, post_title FROM wp_posts LIMIT 5", database="myblog"
        query="SELECT option_value FROM wp_options WHERE option_name='siteurl'"
    """
    exe = _mysql_exe()
    if not exe.exists():
        return f"[Error] mysql.exe not found at {exe}. Check stack_root in Settings."

    s   = _settings()
    cmd = [
        str(exe),
        "--host=127.0.0.1", f"--port={int(s.get('mysql_port', 3306))}",
        "--ssl=0", "-u", "root", "--table",
    ]
    if params.database:
        cmd.append(params.database)
    cmd += ["-e", params.query]

    output, ok = _run(cmd, timeout=15)
    if not ok:
        return f"[MySQL Error] {output}\nTip: Run devstack_get_status to verify MariaDB is running."
    return output


@mcp.tool(
    name="devstack_list_databases",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_list_databases() -> str:
    """
    List all databases in the local MariaDB instance.

    Returns:
        str: Tabular list of database names, or an error message.
    """
    return await devstack_run_mysql_query(MySQLInput(query="SHOW DATABASES;"))


@mcp.tool(
    name="devstack_create_database",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def devstack_create_database(params: CreateDBInput) -> str:
    """
    Create a new MariaDB database with utf8mb4 charset. Safe if it already exists.

    Args:
        params.name (str): Database name — letters, numbers, underscores only.

    Returns:
        str: Success message, or an error message.
    """
    q = MySQLInput(
        query=(
            f"CREATE DATABASE IF NOT EXISTS `{params.name}` "
            f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
    )
    result = await devstack_run_mysql_query(q)
    if "[Error]" in result:
        return result
    return f"✓ Database `{params.name}` is ready."


# ── WP-CLI TOOLS ───────────────────────────────────────────────────────────────

@mcp.tool(
    name="devstack_run_wpcli",
    annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_run_wpcli(params: WPCLIInput) -> str:
    """
    Run a WP-CLI command for a WordPress site on DevStack.

    MariaDB and PHP must be running. The site must have wp-config.php.

    Args:
        params.site_folder (str): htdocs subfolder name (e.g. "myblog")
        params.command     (str): WP-CLI command without the 'wp' prefix.

    Returns:
        str: WP-CLI output, or a "[Error]" message with troubleshooting tips.

    Common commands:
        "plugin list"                              list installed plugins
        "plugin install contact-form-7 --activate" install + activate a plugin
        "plugin update --all"                      update all plugins
        "theme list"                               list themes
        "option get siteurl"                       get site URL
        "option update blogname 'My New Title'"    change site title
        "user list"                                list users
        "user update 1 --user_pass=newpass"        reset admin password
        "cache flush"                              flush object cache
        "db export backup.sql"                     export DB to file
        "search-replace old.com new.com"           replace URL in entire DB
        "post list --post_status=publish"          list published posts
    """
    php  = _php_exe()
    wpcli = _wp_cli()
    site_path = Path(_stack_root()) / "htdocs" / params.site_folder

    if not php.exists():
        return f"[Error] php.exe not found at {php}."
    if not wpcli.exists():
        return (
            f"[Error] wp-cli.phar not found at {wpcli}.\n"
            "Download it from https://wp-cli.org/ and place it in devstack-template/tools/"
        )
    if not site_path.exists():
        return (
            f"[Error] Site folder not found: {site_path}\n"
            "Use devstack_list_sites to see available sites."
        )
    if not (site_path / "wp-config.php").exists():
        return (
            f"[Error] '{params.site_folder}' has no wp-config.php — "
            "it may not be a WordPress site."
        )

    cmd = (
        [str(php), "-d", "phar.readonly=0", str(wpcli)]
        + shlex.split(params.command)
        + [f"--path={site_path}"]
    )
    output, _ = _run(cmd, cwd=str(site_path), timeout=60)
    return output


# ── PHP TOOLS ──────────────────────────────────────────────────────────────────

@mcp.tool(
    name="devstack_run_php",
    annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_run_php(params: PHPInput) -> str:
    """
    Execute a PHP code snippet using the active DevStack PHP runtime.

    Useful for testing functions, checking extensions, reading ini values,
    or debugging before writing code to a file.

    Args:
        params.code        (str): PHP code to run (<?php tag optional).
        params.site_folder (str): Optional site folder to use as working directory.

    Returns:
        str: PHP stdout + stderr output, or an error message.

    Examples:
        code="echo PHP_VERSION;"
        code="var_dump(extension_loaded('gd'));"
        code="echo ini_get('memory_limit');"
        code="$pdo = new PDO('mysql:host=127.0.0.1', 'root', ''); echo 'DB OK';"
    """
    php = _php_exe()
    if not php.exists():
        return f"[Error] php.exe not found at {php}."

    # php -r doesn't want the opening tag
    code = params.code.strip()
    for tag in ("<?php", "<?"):
        if code.startswith(tag):
            code = code[len(tag):].lstrip()

    cwd = None
    if params.site_folder:
        sp = Path(_stack_root()) / "htdocs" / params.site_folder
        if sp.exists():
            cwd = str(sp)

    output, _ = _run(
        [str(php), "-c", str(_php_ini()), "-r", code],
        cwd=cwd, timeout=15,
    )
    return output


@mcp.tool(
    name="devstack_get_php_config",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
async def devstack_get_php_config() -> str:
    """
    Get the active PHP version, loaded extensions list, and key php.ini settings.

    Use this to confirm which PHP is active, diagnose missing extensions,
    or check memory/upload limits before editing php.ini.

    Returns:
        str: JSON with version, php_ini (path), extensions (list),
             memory_limit, upload_max_filesize, post_max_size,
             max_execution_time, display_errors, error_reporting.
    """
    code = r"""
echo json_encode([
    'version'             => PHP_VERSION,
    'php_ini'             => php_ini_loaded_file(),
    'extensions'          => array_values(get_loaded_extensions()),
    'memory_limit'        => ini_get('memory_limit'),
    'upload_max_filesize' => ini_get('upload_max_filesize'),
    'post_max_size'       => ini_get('post_max_size'),
    'max_execution_time'  => ini_get('max_execution_time'),
    'display_errors'      => ini_get('display_errors'),
    'error_reporting'     => ini_get('error_reporting'),
], JSON_PRETTY_PRINT);
"""
    output = await devstack_run_php(PHPInput(code=code))
    try:
        json.loads(output)   # validate it's real JSON
        return output
    except json.JSONDecodeError:
        return json.dumps({"error": "Could not parse PHP output", "raw": output}, indent=2)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
