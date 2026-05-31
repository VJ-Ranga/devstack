# DevStack Manager — AI Agent Context

> Read this file before making any changes. It reflects the actual current state of the codebase.
> Cross-tool standard file — read automatically by most AI coding assistants.

---

## What this project is

**DevStack Manager** is a portable local web development stack for Windows.
It ships a **Python/PySide6 desktop app** that controls Nginx, PHP-CGI, and MariaDB
processes — plus a **PHP web portal + dashboard** served by the stack.

The stack is **Nginx + PHP + MariaDB** (no Apache — it was removed as redundant; Nginx
serves WordPress, Laravel, Drupal, and plain PHP via the `@site_fallback` routing block).

Key differentiator: fully portable — copy the folder to another drive and it works with no reinstall.

---

## How to run

```bash
cd devstack-app
python main.py
```

Or double-click `devstack-app/Run DevStack Manager.bat`.

**Requirements:** Python 3.10+, PySide6 ≥ 6.6.0
Install: `pip install -r devstack-app/requirements.txt`

---

## Repository layout

```
portable-stack-plan/
├── devstack-app/          # Python desktop application
│   ├── main.py            # Entry point — QApplication setup, first-run dialog
│   ├── render_icons.py    # Standalone dev tool: regenerate app + favicon icons
│   ├── core/
│   │   ├── config.py      # load_settings(), save_settings(), load_sites(), save_site()
│   │   ├── service_manager.py   # start/stop/restart, config sync, port conflict detection
│   │   ├── status_reader.py     # reads status via status.ps1 PowerShell script
│   │   ├── version_reader.py    # reads binary versions with 60s cache
│   │   ├── log_reader.py        # tail log files on demand
│   │   ├── installer.py         # discover_php_versions(), SubprocessSQLConnection
│   │   ├── cms_installer.py     # WordPress/Drupal/Laravel/PHP install workers (QThread)
│   │   ├── php_manager.py       # PHP version download worker (QThread)
│   │   └── utils.py             # no_window_flags(), safe_extractall() — shared helpers
│   ├── ui/
│   │   ├── main_window.py       # MainWindow, RefreshWorker, sidebar, status timer
│   │   ├── styles.py            # build_stylesheet(), FLUENT_GLYPHS, set_status()
│   │   ├── widgets.py           # ClickableFrame, QuickAccessCard, SidebarButton
│   │   ├── theme_light.qss / theme_dark.qss
│   │   ├── tabs/
│   │   │   ├── overview_tab.py  # Control tab: status grid + Start/Stop/Restart All
│   │   │   ├── services_tab.py  # Services tab: per-service rows
│   │   │   ├── websites_tab.py  # Websites tab: site rows, install, search, Terminal/Code btns
│   │   │   ├── logs_tab.py      # Logs tab: source selector, search, auto-refresh
│   │   │   └── settings_tab.py  # Settings tab: ports, PHP limits, extension manager
│   │   └── dialogs/
│   │       ├── cms_install_dialog.py   # Install Website dialog
│   │       ├── customize_dialog.py     # UI Customize dialog (colors, radius, font, height)
│   │       └── first_run_dialog.py     # One-time welcome checklist
│   └── config/
│       ├── app-settings.json    # User settings (gitignored)
│       └── sites.json           # Registered sites — never stores admin_pass (gitignored)
│
├── devstack-mcp/          # MCP server exposing the stack to AI agents
│   └── server.py          # 13 tools: status, logs, mysql, wp-cli, php, etc.
│
├── devstack-template/     # The actual stack binaries + config
│   ├── nginx/conf/nginx.conf   # Main (only) web server — port 80
│   ├── mysql/my.ini       # MariaDB
│   ├── php/, php84/       # PHP runtimes (active one chosen in Settings)
│   ├── htdocs/
│   │   ├── index.php             # DevStack Local Portal (site list + live status)
│   │   ├── dashboard/index.php   # Read-only status dashboard (stat strip + services)
│   │   ├── dashboard/api.php     # JSON status endpoint (services + php_version + site_count)
│   │   ├── dashboard/style.css
│   │   └── phpmyadmin/
│   ├── cache/             # CMS download cache (7-day TTL)
│   └── tools/
│       ├── status.ps1     # PowerShell: returns JSON service health (also the stack-root marker)
│       └── wp-cli.phar    # WP-CLI for WordPress installs
│
├── AGENTS.md              # ← you are here (AI context)
├── UI-RULES.md            # Strict UI design rules — read before changing any UI
├── README.md
├── PROJECT-DOCS.md        # Human-facing project documentation
├── SECURITY_AUDIT.md      # Security findings (all fixed)
├── CODE_QUALITY_AUDIT.md  # Code quality findings (all fixed)
└── DX_AUDIT.md            # Developer experience findings
```

---

## Architecture — critical patterns

### QThread worker pattern

Every background operation uses a dedicated `QThread` subclass. **Do not null the worker
reference inside its `finished` signal handler** — the C++ object may still be running when
the Python signal fires and causes a `libshiboken: Internal C++ object already deleted` crash.

```python
# CORRECT pattern (used everywhere in this codebase)
def _on_done(self, result):
    # DO NOT do: self._worker = None  ← crash
    self._re_enable_buttons()
    # The worker reference is cleared at the START of the next _run() call instead

def _run_action(self):
    if self._worker and self._worker.isRunning():
        return
    self._worker = None          # safe here — isRunning() returned False
    self._worker = MyWorker(...)
    self._worker.finished.connect(self._on_done)
    self._worker.start()
```

### Service start/stop flow

`service_manager.start()` does this in order (`START_ORDER = ["mysql", "php", "nginx"]`):
1. Load settings (ports, active PHP folder)
2. Sync nginx.conf + my.ini to disk with correct paths/ports
3. Kill any existing process (clean restart)
4. Spawn new processes (PHP spawns 3 independent php-cgi.exe instances)
5. Wait for each to appear in `tasklist`; on failure, report the conflicting process via `netstat`
6. Return `{"success": True}` or `{"success": False, "error": "..."}`

There are exactly **3 services: mysql, php, nginx**. There is no Apache.

### Config files are placeholder-synced

`nginx.conf` and `my.ini` store paths as `DEVSTACK_ROOT/...` placeholders. On every
start, `_sync_*_config()` regex-replaces them with the real absolute path. **Never hardcode an
absolute path in these files** — it will be overwritten and breaks portability.
`php.ini` uses a relative `extension_dir = "ext"` for the same reason.

### Settings storage

- `app-settings.json` — all user settings, loaded via `load_settings()` merged with `DEFAULT_SETTINGS`.
- `sites.json` — registered websites. **Never stores `admin_pass`.**
- Both files are **gitignored**.

---

## UI rules (summary — full rules in UI-RULES.md)

- **Style:** Windows 11 utility — calm, flat, scannable. NOT a dashboard/startup-page aesthetic.
- **Fonts:** Segoe UI for UI, Consolas for logs/code.
- **One primary button per group.** Secondary = neutral border. Destructive = red for Stop/Delete.
- **Status colors:** green=running, amber=partial, red=stopped. Never flood large areas with these.
- **Service rows** = name + role + port + status badge + actions. Readable in one horizontal scan.
- **Logs are secondary.** Manual load by default. Auto-refresh is opt-in.
- **Settings = plain forms.** No decorative metric blocks.

When adding UI, check `UI-RULES.md` first.

---

## Key conventions

### Python
- Minimum Python 3.10. Type hints use `str | None` union syntax.
- Subprocess calls always pass `creationflags=no_window_flags()` (from `core/utils.py`).
- Zip extraction always uses `safe_extractall()` from `core/utils.py` — never bare `zipfile.extractall()`.
- Spinboxes/combos in Settings use `GuardedSpinBox`/`GuardedComboBox` (only react to scroll when hovered).

### Security rules already applied
- `admin_pass` is never saved to `sites.json`.
- Downloads verify SHA256 when a hash is configured (PHP manager).
- Zip Slip blocked in all extraction paths via `safe_extractall()`.
- The web dashboard is **read-only** — no service control from the browser (use the desktop app).

### PHP web layer
- `htdocs/index.php` is the portal (lists sites, polls `dashboard/api.php` for live status).
- `htdocs/dashboard/index.php` is a read-only status monitor.
- `dashboard/api.php` runs `status.ps1` and returns JSON.
- Nginx `@site_fallback` routes `/<site>/<anything>` to that site's own `index.php` so each
  CMS/site handles its own 404 (WordPress, Laravel, Drupal, plain PHP).

---

## Common tasks

### Add a new CMS/framework to the installer
1. Add entry to `CMS_OPTIONS` and `CMS_NOTES` in `core/cms_installer.py`
2. Add `_install_<name>()` method to `CMSInstallWorker`
3. Route it in `run()` via `elif app_id == "<name>"`
4. Add detection logic in `websites_tab.py:_scan_and_import()` and `htdocs/index.php`

### Add a new PHP version to the downloader
1. Add entry to `STABLE_PHP_VERSIONS` in `core/php_manager.py`
2. Include `sha256` field (from windows.php.net) and `eol_warning` if applicable

### Add a new setting
1. Add default to `DEFAULT_SETTINGS` in `core/config.py`
2. Add widget to `settings_tab.py:_setup_ui()`, read in `_load_settings()`, write in `_save_settings()`

### Add a new tab
1. Create `ui/tabs/newtab.py` extending `QWidget`; implement `apply_density()` if it has buttons
2. In `main_window.py`: instantiate, add to `self.pages`, add sidebar nav entry, add to `closeEvent` workers

---

## Known gotchas

| Gotcha | Detail |
|--------|--------|
| `PHP_FCGI_CHILDREN` | Ignored on Windows. DevStack spawns 3 independent `php-cgi.exe` processes instead. |
| OPcache | Must be enabled in each `php*/php.ini` — biggest WordPress speed win. CLI stays off (`opcache.enable_cli=0`). |
| Icon glyphs | Use Segoe **MDL2 Assets** codepoints (0xE7xx/0xE8xx) — they exist on Win10 + Win11. Fluent-only codepoints (e.g. 0xEFC3) render as empty boxes on Win10. |
| `QFont(css_font_list)` | `QFont()` takes a single family name, not a CSS comma list. Use `"Consolas"`. |
| Worker null-in-signal | Never null a QThread worker inside its `finished` signal — see QThread pattern above. |
| Config path sync | Never hardcode paths in nginx/mysql configs — use `DEVSTACK_ROOT` placeholder. |
| Stack-root marker | `find_stack_root()` detects the stack by checking `tools/status.ps1` exists. |
| `no_window_flags()` | Always pass to subprocess on Windows or a console window flashes. From `core/utils.py`. |

---

## What NOT to do

- Do not store `admin_pass` in `sites.json` or any config file.
- Do not use bare `zipfile.extractall()` — always use `safe_extractall()` from `core/utils.py`.
- Do not call `load_settings()` multiple times in a single worker run — load once, cache in `self._cached_settings`.
- Do not add CSS-style font lists to `QFont()`.
- Do not hardcode absolute paths in nginx/mysql config files.
- Do not add service start/stop controls to the web dashboard — it is read-only by design.
- Do not make the UI decorative — no gradients, no heavy shadows, no colored non-status backgrounds.
- Do not add `--allow-root` to WP-CLI commands. Do not use `shell=True` in subprocess.
- Do not add performance directives to nginx that hurt localhost (gzip, tcp_nopush, open_file_cache).
