# DevStack Project Documentation

## What This Project Is

DevStack Manager is a **portable local web development stack for Windows**. It provides:

1. A **Python/PySide6 desktop application** to control the stack
2. A **PHP web portal + dashboard** served by the stack itself
3. An **MCP server** so AI coding agents can interact with the stack

The goal: run and manage WordPress, Laravel, Drupal, and plain PHP projects locally,
with a clean UI and zero-reinstall portability.

---

## Stack Services

| Service | Role | Default Port |
|---------|------|--------------|
| **Nginx** | Web server / entry point | 80 |
| **PHP FastCGI** | Runs PHP (3 php-cgi processes) | 9000 |
| **MariaDB** | Database | 3306 |

"Start All" launches all three. There is no Apache — Nginx serves WordPress, Laravel,
Drupal, and plain PHP directly (it's the standard modern WordPress stack).

---

## Desktop App

### Entry point
`devstack-app/main.py` — sets up the QApplication, applies the Windows style/palette,
loads the icon, shows the main window, and displays the first-run welcome on first launch.

### Tabs
- **Control** (`overview_tab.py`) — status grid, Start/Stop/Restart all, quick links
- **Websites** (`websites_tab.py`) — install sites, per-site PHP, Terminal/VS Code/Files/PHP Info, search
- **Services** (`services_tab.py`) — per-service control rows
- **Logs** (`logs_tab.py`) — log viewer with search + optional auto-refresh
- **Settings** (`settings_tab.py`) — ports, PHP limits, debug mode, extensions, PHP downloader

### Dialogs
- `cms_install_dialog.py` — Install Website (WordPress/Drupal/Laravel/PHP)
- `customize_dialog.py` — UI customization (colors, radius, font size, button height)
- `first_run_dialog.py` — one-time welcome checklist

### Core layer (`devstack-app/core/`)
- `config.py` — settings + site registry load/save, stack-root detection
- `service_manager.py` — start/stop/restart, config sync, port-conflict detection
- `status_reader.py` — reads service health via `status.ps1`
- `version_reader.py` — reads binary versions (60s cache)
- `log_reader.py` — tails log files on demand
- `installer.py` — PHP version discovery, MySQL connection helper
- `cms_installer.py` — WordPress/Drupal/Laravel/PHP install workers (QThread)
- `php_manager.py` — PHP runtime downloader (QThread)
- `utils.py` — `no_window_flags()`, `safe_extractall()`

---

## Web Layer (`devstack-template/htdocs/`)

- **`index.php`** — DevStack Local Portal at `http://localhost/`. Lists detected sites as
  cards (WordPress/Laravel/Drupal/PHP) and shows live service status by polling `dashboard/api.php`.
- **`dashboard/index.php`** — read-only status dashboard.
- **`dashboard/api.php`** — runs `status.ps1`, returns JSON. Polled by JS every 5s.
- **`dashboard/style.css`** — shared dashboard styling.

The web layer is **read-only** — service control lives in the desktop app.

### Nginx routing
`nginx.conf` uses a `@site_fallback` block that routes `/<site>/<anything>` to that
site's own `index.php`. This makes WordPress permalinks, Laravel routes, Drupal clean
URLs, and plain-PHP 404 handling all work in subfolders.

---

## Portability — How It Works

Config files (`nginx.conf`, `httpd.conf`, `my.ini`) store paths as a `DEVSTACK_ROOT`
placeholder. On every start, `service_manager._sync_*_config()` regex-replaces the
placeholder with the real absolute path of wherever the folder currently lives.
`php.ini` uses a relative `extension_dir = "ext"`.

Result: move the folder to any drive or machine, start the app, and every path is
corrected automatically. **Never hardcode absolute paths in these config files.**

---

## Performance

- **OPcache** enabled in each `php*/php.ini` (CLI off) — main WordPress speedup.
- **MariaDB** tuned for dev: 256M buffer pool, `flush_log_at_trx_commit=2`, query cache off.
- **Nginx** kept minimal — deliberately no gzip / tcp_nopush / open_file_cache, which
  only add latency on localhost.

---

## Tools (`devstack-template/tools/`)

- `status.ps1` — returns JSON service health (used by the app and `api.php`); also the
  marker file `find_stack_root()` uses to locate the stack
- `wp-cli.phar` — WP-CLI, used by the WordPress installer and the MCP server

---

## MCP Server (`devstack-mcp/server.py`)

Exposes 13 tools to AI coding agents (Claude Code, Cursor, etc.): stack status, site
list/info, log reading, service start/stop/restart, MySQL queries, database create/list,
WP-CLI commands, PHP code execution, and PHP config inspection. Configured via the
project's MCP settings; runs over stdio.

---

## Running

### Desktop app
```bash
cd devstack-app
python main.py
```
Or `devstack-app/Run DevStack Manager.bat`.

### Web portal
After Start All: `http://localhost/`

---

## Documentation Map

| File | Purpose |
|------|---------|
| `README.md` | Quick start + overview |
| `PROJECT-DOCS.md` | This file — full documentation |
| `AGENTS.md` | AI agent context (architecture, conventions, gotchas) |
| `UI-RULES.md` | Strict UI design rules |
| `SECURITY_AUDIT.md` | Security findings (all fixed) |
| `CODE_QUALITY_AUDIT.md` | Code quality findings (all fixed) |
| `DX_AUDIT.md` | Developer experience findings |

---

## Key Files to Read First

1. `PROJECT-DOCS.md` / `AGENTS.md`
2. `UI-RULES.md`
3. `devstack-app/main.py`
4. `devstack-app/ui/main_window.py`
5. `devstack-app/core/service_manager.py`
6. `devstack-app/core/status_reader.py`
7. `devstack-template/tools/status.ps1`
8. `devstack-template/htdocs/index.php`
