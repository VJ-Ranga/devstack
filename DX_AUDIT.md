# Developer Experience (DX) Audit

**Compared against:** Laragon, XAMPP, Herd, Local by Flywheel  
**Target user:** PHP developer running WordPress / Laravel / Drupal locally on Windows  

---

## Overall Score: 6.5 / 10

The app is **well-built and clean**. It looks good, starts fast, and the core service management works. But side-by-side with Laragon (the closest competitor on Windows), a developer would switch back after 10 minutes because of friction in the daily workflow. All the gaps are fixable.

---

## ✅ What works well

| Thing | Why it's good |
|-------|--------------|
| One-click Start/Stop All | Zero friction for the most common action |
| Auto PHP version switching | Rare in free tools — this is a real differentiator |
| CMS installer with MariaDB pre-flight | Saves minutes of manual setup |
| Portable / no install | Huge advantage — USB drive / cloud sync ready |
| Clean UI, no clutter | Follows UI-RULES.md well — calm, scannable |
| Dark mode | Expected by developers |
| Log viewer per service | Better than nothing and better than file hunting |
| Extension manager | One-click enable/disable beats editing php.ini manually |

---

## 🔴 High Friction — Developers will hit these every day

---

### F1 — No Terminal Button on Site Rows

**Impact: Critical**

In Laragon and Herd, right-clicking a site (or pressing a button) opens a terminal `cd`'d into the project folder. This is the #1 most-used action after "Open site". Developers need to run `php artisan`, `composer install`, `wp cli`, `npm run dev` constantly.

Right now the only option is: click "Files" → navigate to the folder → open a terminal manually.

**Fix:**
```python
# In SiteRow._setup_row(), add a Terminal button
terminal_btn = QPushButton("Terminal")
terminal_btn.setObjectName("DefaultButton")
terminal_btn.clicked.connect(self._open_terminal)
row1.addWidget(terminal_btn, 0, Qt.AlignVCenter)

def _open_terminal(self):
    import subprocess
    path = str(Path(self.tab.main_window.get_stack_root()) / "htdocs" / self.site.get("folder"))
    subprocess.Popen(["cmd.exe", "/K", f"cd /d {path}"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    # Or PowerShell: ["powershell.exe", "-NoExit", "-Command", f"cd '{path}'"]
```

---

### F2 — Site URL Not Shown Anywhere in Site Rows

**Impact: Critical**

Every site row shows: badge, folder path, credentials, action buttons. The **actual URL** (`http://localhost/mysite`) is invisible. A developer has to mentally reconstruct it from port + folder name.

Laragon shows the full URL, makes it clickable, and puts a "Copy URL" button next to it.

**Fix:** Add URL label + copy button to each `SiteRow`:
```python
port = int(self.tab.main_window.settings.get("nginx_port", 80))
base = f"http://localhost:{port}" if port != 80 else "http://localhost"
suffix = "public/" if app_id == "laravel" else ""
url = f"{base}/{folder}/{suffix}"

url_lbl = QLabel(url)
url_lbl.setObjectName("RowMeta")
url_lbl.setTextFormat(Qt.PlainText)
copy_url_btn = self._icon_btn(_GLYPH["copy"], "Copy URL", lambda u=url: self._copy_to_clipboard(u, "URL"))
```

---

### F3 — Logs Don't Auto-Load, No Search, No Tail

**Impact: High**

The Logs tab shows "Select a log source and click Refresh" on launch. Every time you switch to it, you have to manually click Refresh. There's no auto-refresh, no search/filter, and no tail mode (follow new entries in real time).

When PHP crashes, you go to Logs, click Refresh, scroll to the bottom, manually look for the error. This is slow.

**Fix (three small changes):**

1. **Auto-load last selected source on tab switch** — connect `_on_tab_changed(3)` to `_load_log()`  
2. **Add a search bar:**
```python
self.search_input = QLineEdit()
self.search_input.setPlaceholderText("Filter log...")
self.search_input.textChanged.connect(self._filter_log)
```
3. **Add Auto-Refresh toggle** — a checkbox that triggers `QTimer` every 3 s calling `_load_log()`

---

### F4 — Per-Site PHP Override Only Works on Apache, Silently Broken on Nginx

**Impact: High**

`_apply_php_version()` writes `.htaccess` with `SetHandler "proxy:fcgi://..."`. Apache reads `.htaccess`. **Nginx ignores `.htaccess` entirely.** If the developer is using Nginx (port 80, which is the default entry point), the PHP version override does nothing — silently.

There's no warning, no indicator that this feature only works through Apache.

**Fix (two options):**
- Show a warning toast when Nginx is the active frontend: *"PHP override via .htaccess only applies when accessing through Apache (port 8088). Nginx ignores .htaccess files."*
- Or implement per-site Nginx location blocks as the real solution.

---

### F5 — Settings "Enable Editing" Checkbox Is Non-Standard and Confusing

**Impact: Medium-High**

Every settings section has a `☐ Enable Editing` checkbox that must be ticked before any field becomes editable. This pattern exists nowhere else in standard desktop software. A new user will stare at the greyed-out fields wondering if the settings loaded correctly.

The intent (prevent accidental port changes) is good but the execution is not. Standard Windows pattern is: just let fields be editable, confirm on Save.

**Fix:** Remove the checkbox guards entirely. Add a confirmation dialog in `_save_settings()` only if ports have changed:
```python
if any port changed:
    reply = QMessageBox.question(self, "Confirm Port Change",
        "Changing ports will restart all services. Continue?")
    if reply != QMessageBox.Yes:
        return
```

---

## 🟠 Medium Friction — noticed within the first hour

---

### F6 — Port Conflict Error Is Not Actionable

When a service fails to start, the error is:
```
Nginx failed to start. Check port 80 for conflicts.
```

This tells the developer nothing about *what* is using port 80. Laragon shows the process name and PID.

**Fix:** Use `netstat` to identify the conflicting process before showing the error:
```python
def _find_port_user(port: int) -> str:
    r = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True, timeout=5
    )
    for line in r.stdout.splitlines():
        if f":{port} " in line and "LISTENING" in line:
            pid = line.strip().split()[-1]
            r2 = subprocess.run(["tasklist", "/fi", f"PID eq {pid}", "/nh"],
                capture_output=True, text=True)
            return r2.stdout.strip().split()[0] if r2.stdout.strip() else f"PID {pid}"
    return "unknown process"
```
Error becomes: *"Port 80 is in use by: IIS Express (PID 1234). Stop it or change the Nginx port."*

---

### F7 — No "Open in VS Code" (or Any Editor)

**Impact: Medium**

Every modern local dev tool has this. It's one button that opens the project root in the configured editor. Developers switch between the app and their editor constantly.

**Fix:** Add to site row alongside "Files" button. Check for VS Code, Cursor, PhpStorm in order:
```python
def _open_in_editor(self):
    path = str(stack_root / "htdocs" / folder)
    for exe in ["code", "cursor", "phpstorm64", "phpstorm"]:
        if shutil.which(exe):
            subprocess.Popen([exe, path])
            return
    QMessageBox.information(self, "No editor found",
        "VS Code, Cursor, or PhpStorm not found in PATH.")
```

---

### F8 — No `display_errors` / Debug Mode Toggle in PHP Settings

**Impact: Medium**

The PHP settings panel lets you set memory_limit, upload size, timeouts — but not `display_errors = On/Off`. Toggling PHP error display is the most frequent php.ini change during development.

**Fix:** Add a toggle checkbox to the PHP Runtime panel:
```python
self.display_errors_cb = QCheckBox("Display errors in browser (development mode)")
```
And write `display_errors = On` / `error_reporting = E_ALL` to php.ini when saving.

---

### F9 — Laravel Installation Ends With "Run composer install yourself"

**Fix:** After extracting Laravel, check if `composer` is in PATH and offer to run it:
```python
if shutil.which("composer"):
    self.log_emitted.emit("Composer found — running 'composer install'...")
    subprocess.run(["composer", "install", "--no-interaction"],
                   cwd=str(target), ...)
else:
    self.log_emitted.emit("[INFO] Composer not found in PATH. Run 'composer install' manually.")
```

---

### F10 — No phpinfo Per Site

**Impact: Medium**

The Quick Access Hub on the Overview tab has one global "PHP Info" link (`/phpinfo.php`). But if a developer changed the per-site PHP version, they need to confirm *that site's* PHP version, not the global one.

**Fix:** Add `phpinfo.php` generation per site during `_install_plain_php()` and `_wordpress_direct_download()`, and add a "PHP Info" link in each site row.

---

### F11 — No Custom Local Domain Support

**Impact: Medium**

Laragon auto-configures `mysite.test` domains via hosts file edits + nginx virtual hosts. DevStack requires you to know the port and folder name and use `localhost/folder`.

This is a significant UX gap for professional workflows where sites need to be at `myproject.local`.

**Partial Fix (minimum viable):** Add a "Custom Domain" field to the site row. When set, write to Windows hosts file and generate an nginx server block. This is a bigger feature but worth tracking.

---

## 🔵 Low Friction — polish items

---

### F12 — README Is Too Short for Onboarding

The README.md is 64 lines. A new developer cloning the repo doesn't know:
- What Python version is required
- How to install PySide6
- Where to get the `devstack-template` folder
- How to run for the first time
- What the `devstack-grants.sql` does

**Fix:** Add a "Getting Started" section with exact commands.

---

### F13 — No First-Run Welcome / Checklist

First launch shows the Control tab with all services stopped. A brand-new user sees red "Stopped" badges and no guidance. There's no "here's what to do first" message.

**Fix:** On first run (detect by `app-settings.json` not existing), show a simple startup checklist:
1. ✅ App started
2. ☐ Click "Start All" to launch services  
3. ☐ Open phpMyAdmin to verify database
4. ☐ Create your first website

---

### F14 — "Needs Attention" Badge State Has No Explanation

When a service shows "Needs Attention" (partial state — process running but port not listening), there's no tooltip or detail explaining what that means. A developer seeing this for the first time doesn't know if it's a crash, a slow start, or a config problem.

**Fix:** Add a tooltip to the badge:
```python
badge.setToolTip("Process is running but the port is not yet listening. "
                 "This may resolve in a few seconds, or indicate a config error.")
```

---

### F15 — Websites Tab Has No Search When List Gets Long

With 10+ projects, scrolling through the list to find one is slow. No filter.

**Fix:** Add a search `QLineEdit` above the list that filters `SiteRow` widgets by folder/title in real time.

---

## Summary — Priority Fix Order

| Priority | Fix | Effort |
|----------|-----|--------|
| 🔴 1 | Terminal button per site (F1) | 1–2 hours |
| 🔴 2 | Show site URL + copy button in row (F2) | 1 hour |
| 🔴 3 | Log auto-load + search (F3) | 2–3 hours |
| 🔴 4 | Warn that per-site PHP only works on Apache (F4) | 30 min |
| 🟠 5 | Remove "Enable Editing" checkbox guards (F5) | 1 hour |
| 🟠 6 | Port conflict → show what's using the port (F6) | 1–2 hours |
| 🟠 7 | Open in VS Code / editor button (F7) | 1 hour |
| 🟠 8 | display_errors toggle in PHP settings (F8) | 30 min |
| 🟠 9 | Auto-run composer for Laravel installs (F9) | 1 hour |
| 🔵 10 | phpinfo per site (F10) | 30 min |
| 🔵 11 | First-run welcome checklist (F13) | 2 hours |
| 🔵 12 | Tooltip for "Needs Attention" state (F14) | 15 min |
| 🔵 13 | Search in websites list (F15) | 1 hour |

---

*Total estimated effort to reach 9/10 DX: ~15–20 hours of focused work.*
