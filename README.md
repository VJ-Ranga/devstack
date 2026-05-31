# DevStack Manager (Portable)

A portable local web development stack for Windows — manage Nginx, PHP, and MariaDB
from a clean desktop app. Install WordPress, Laravel, Drupal, or plain PHP projects
in a couple of clicks.

**Fully portable** — copy the folder to another drive or machine and it just works.
All config paths are auto-synced on every start.

## Screenshot

![DevStack Manager](DevStack.png)

## Getting Started

```bash
# 1. Install dependencies (first time only)
pip install -r devstack-app/requirements.txt

# 2. Run the app
cd devstack-app
python main.py
```

Or double-click **`devstack-app/Run DevStack Manager.bat`**.

**Requirements:** Windows, Python 3.10+, PySide6 ≥ 6.6.0

## First Run

1. A welcome checklist appears on first launch.
2. Go to the **Control** tab → click **Start All** (starts Nginx + PHP + MariaDB).
3. Open **http://localhost/** — the DevStack Local Portal lists all your sites.
4. Use **Websites → Install Website** to create a WordPress/Laravel/Drupal/PHP project.

## Desktop App Tabs

- **Control** — overall status, Start/Stop/Restart all, quick links
- **Websites** — install sites, per-site PHP version, Terminal / VS Code / Files / PHP Info buttons, search
- **Services** — start/stop/restart individual services (Nginx, PHP, MariaDB)
- **Logs** — view service logs with search + optional auto-refresh
- **Settings** — ports, PHP limits, debug mode, extension manager, PHP downloader
- **Top menu** — UI Customize (colors, radius, fonts), About

## Web Layer

- **http://localhost/** — Local Portal: site cards + live service status
- **http://localhost/dashboard/** — read-only status dashboard
- **http://localhost/phpmyadmin/** — database admin

The web layer is read-only. Use the desktop app to start/stop services.

## Website Types (auto-detected)

| Type | Detected by | URL |
|------|-------------|-----|
| WordPress | `wp-config.php` / `wp-includes/` | `/site/` |
| Laravel | `artisan` | `/site/public/` |
| Drupal | `core/lib/Drupal.php` | `/site/` |
| Plain PHP | (default) | `/site/` |

Each site handles its own 404s — Nginx routes `/<site>/<anything>` to that site's `index.php`.

## PHP Version

The active PHP version is set globally in **Settings → PHP Runtime Management**. Download
additional PHP versions there and switch the active one — it applies to all sites
(Nginx routes every site through the same PHP-CGI pool).

## Performance Notes

- **OPcache** is enabled in each PHP runtime — the biggest WordPress speed win.
- MariaDB is tuned for local dev (`innodb_buffer_pool_size`, `flush_log_at_trx_commit=2`).
- Nginx config is kept minimal — no gzip/buffering directives that only slow down localhost.

## AI Assistant Support

The repo ships context files for AI coding tools:
- `AGENTS.md` — cross-tool project context (read by most assistants)
- `.cursor/rules/` — Cursor rules
- `.github/copilot-instructions.md` — Copilot instructions
- `devstack-mcp/server.py` — MCP server: live stack status, logs, MySQL, WP-CLI, PHP exec

## Repo Structure

```
portable-stack-plan/
├── devstack-app/        Python desktop application (core/ + ui/)
├── devstack-mcp/        MCP server for AI agents
├── devstack-template/   Stack binaries + config (nginx, mysql, php, htdocs)
├── AGENTS.md            AI context
├── UI-RULES.md          UI design rules
└── PROJECT-DOCS.md      Full documentation
```

---

Developed by [VJ-Ranga](https://vjranga.com).
