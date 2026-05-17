# DevStack Project Docs

## What This Project Is

This project is a local development stack controller for Windows.

It has **two interfaces** for the same stack:

1. a **desktop application** built with Python and PySide6
2. a **web dashboard** served from the local stack itself

The goal is simple:

- start the stack
- stop the stack
- restart the stack
- check service status
- open the main tools quickly

This project is intentionally **not** an app installer, site provisioner, or WordPress manager anymore.

## Main Features

### Desktop app

- Control Center page
- Services page
- Logs page
- Settings page
- quick open buttons for:
  - Nginx
  - Apache
  - phpMyAdmin
  - Web Interface

### Web dashboard

- overall stack status
- start / stop / restart all
- service list with per-service actions
- quick links to main tools
- optional logs section

## Stack Services

The stack is built around these services:

- **Apache**
- **Nginx**
- **PHP FastCGI**
- **MariaDB**

## Project Structure

```text
portable-stack-plan/
├─ devstack-app/
│  ├─ assets/
│  │  └─ icon assets for the desktop app
│  ├─ config/
│  │  └─ app-settings.json
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ log_reader.py
│  │  ├─ service_manager.py
│  │  ├─ status_reader.py
│  │  └─ version_reader.py
│  ├─ ui/
│  │  ├─ main_window.py
│  │  ├─ styles.py
│  │  └─ tabs/
│  │     ├─ overview_tab.py
│  │     ├─ services_tab.py
│  │     ├─ logs_tab.py
│  │     └─ settings_tab.py
│  ├─ Create Desktop Shortcut.ps1
│  ├─ Run DevStack Manager.bat
│  ├─ build.spec
│  ├─ main.py
│  └─ requirements.txt
├─ devstack-template/
│  ├─ _downloads/
│  │  └─ downloaded stack archives
│  ├─ apache/
│  ├─ htdocs/
│  │  ├─ dashboard/
│  │  │  └─ index.php
│  │  └─ phpmyadmin/
│  ├─ mysql/
│  ├─ nginx/
│  ├─ php/
│  ├─ start.bat
│  ├─ start.cmd
│  ├─ stop.bat
│  └─ tools/
│     ├─ control.ps1
│     ├─ download-binaries.ps1
│     └─ status.ps1
├─ UI-RULES.md
└─ PROJECT-DOCS.md
```

## Desktop App Architecture

### Entry point

- `devstack-app/main.py`

This file:

- creates the Qt application
- applies the Windows-like style and palette
- loads the app icon
- opens the main window

### Main window

- `devstack-app/ui/main_window.py`

This file:

- creates the tab layout
- owns the shared refresh worker
- keeps status updates in sync across tabs
- provides helper methods for opening URLs

### Core layer

- `devstack-app/core/config.py`
  - app settings loading and saving
- `devstack-app/core/service_manager.py`
  - starts, stops, and restarts services
- `devstack-app/core/status_reader.py`
  - reads stack status from PowerShell
- `devstack-app/core/version_reader.py`
  - reads service versions with caching
- `devstack-app/core/log_reader.py`
  - reads recent log output on demand

### UI layer

- `devstack-app/ui/styles.py`
  - shared design tokens and styling helpers
- `devstack-app/ui/tabs/overview_tab.py`
  - control center
- `devstack-app/ui/tabs/services_tab.py`
  - direct per-service controls
- `devstack-app/ui/tabs/logs_tab.py`
  - manual log inspection
- `devstack-app/ui/tabs/settings_tab.py`
  - stack path, ports, refresh interval, density

## Web Dashboard Architecture

### Dashboard entry point

- `devstack-template/htdocs/dashboard/index.php`

This file:

- receives start/stop/restart actions from forms
- calls PowerShell control scripts
- reads service status from `status.ps1`
- builds the quick links
- optionally loads logs
- renders the dashboard UI

### Stack scripts

- `devstack-template/tools/control.ps1`
  - controls service start/stop/restart
- `devstack-template/tools/status.ps1`
  - returns JSON service health
- `devstack-template/tools/download-binaries.ps1`
  - helps fetch stack binaries

## How It Works

### Desktop flow

1. user opens the desktop app
2. main window starts a shared refresh worker
3. refresh worker reads:
   - service status
   - version information
4. results are pushed into the UI tabs
5. when the user clicks a control button:
   - the app starts a background service worker
   - the PowerShell / process logic runs
   - the UI refreshes again after the action

### Web flow

1. user opens `/dashboard/`
2. PHP reads current stack status from `status.ps1`
3. page renders service rows and actions
4. when the user submits an action form:
   - PHP runs `control.ps1`
   - page reloads with updated notice/state

## UI Standard

The UI standard is defined in:

- `UI-RULES.md`

Important points from that document:

- use a plain Windows 11 utility style
- avoid decorative dashboard cards
- prefer flat sections and rows
- use one primary action per group
- use color for status meaning only
- keep logs secondary
- keep settings plain and form-based

## Dependencies

Desktop app requirements:

- `PySide6>=6.6.0`
- `requests>=2.31.0`

These are listed in:

- `devstack-app/requirements.txt`

## Running The Project

### Run desktop app

From `devstack-app/`:

```bat
Run DevStack Manager.bat
```

Optional shortcut helper:

```powershell
Create Desktop Shortcut.ps1
```

### Run stack manually

From `devstack-template/`:

```bat
start.bat
stop.bat
```

### Open web dashboard

After the stack is running:

```text
http://localhost/dashboard/
```

## Build / Packaging

The desktop app includes:

- `devstack-app/build.spec`

This is a PyInstaller spec file for packaging the app into a Windows executable.

Current packaging notes:

- app entry: `main.py`
- windowed app: `console=False`
- icon: `assets/icon.ico`

## Current Product Direction

The current product direction is:

- local stack control tool
- desktop app + web dashboard
- start/stop/open workflow
- simple service management
- optional logs

The current product is **not** intended to include:

- WordPress provisioning
- app installation flows
- bundled demo sites
- decorative dashboard UI experiments

## Files That Matter Most

If someone new needs to understand the project quickly, read these first:

1. `PROJECT-DOCS.md`
2. `UI-RULES.md`
3. `devstack-app/main.py`
4. `devstack-app/ui/main_window.py`
5. `devstack-app/core/service_manager.py`
6. `devstack-app/core/status_reader.py`
7. `devstack-template/tools/control.ps1`
8. `devstack-template/tools/status.ps1`
9. `devstack-template/htdocs/dashboard/index.php`

## Current Notes

- The desktop app and web dashboard now target the same simpler workflow.
- The old WordPress/app-installer paths were removed.
- The project still contains stack binaries and downloaded archives under `devstack-template/`.
- The UI is being rebuilt around the rules in `UI-RULES.md`.

## Summary

This project is a Windows local stack control system with:

- a Python desktop controller
- a PHP web dashboard
- shared service-control behavior
- simplified UI rules
- a clear focus on stack management instead of app/site installation
