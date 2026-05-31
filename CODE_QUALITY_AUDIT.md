# Code Quality Audit — Full Codebase

**Date:** 2026-05-30  
**Scope:** All Python + PHP files — dead code, duplicates, bad logic, unused imports  

---

## Summary

| Category | Count |
|----------|-------|
| 🔴 Bug / Wrong behaviour | 3 |
| 🟠 Missed Security Fix | 1 |
| 🟡 Dead / Unused code | 6 |
| 🔵 Code smell / Duplicate | 4 |

---

## 🔴 Bugs / Wrong Behaviour

---

### B1 — `_apply_php_version()` Port Calculation is Broken

**File:** `ui/tabs/websites_tab.py:425–427`

```python
suffix = selected_folder.replace("php", "").strip()
port   = 9000 + int(suffix) if suffix.isdigit() else 9000
block  = f'SetHandler "proxy:fcgi://127.0.0.1:{port}"'
```

`php84` → suffix = `"84"` → port = `9084`. Nothing listens on port 9084. The per-site PHP selector writes an `.htaccess` pointing at a port that doesn't exist. The correct port is always the `php_port` from settings (`9000` by default), because all PHP versions share the same FastCGI port when using the manager.

**Fix:** Remove the port arithmetic. Always use the configured PHP port:

```python
from core.config import load_settings
php_port = int(load_settings().get("php_port", 9000))
block = (f"{marker_s}\n<FilesMatch \\.php$>\n"
         f"    SetHandler \"proxy:fcgi://127.0.0.1:{php_port}\"\n"
         f"</FilesMatch>\n{marker_e}\n")
```

---

### B2 — `QFont(MONO_FONT, 10)` Receives CSS Font List — Font Never Loads

**File:** `ui/styles.py:5` · `ui/tabs/logs_tab.py:62`

```python
MONO_FONT = '"Cascadia Code", "Consolas"'   # styles.py
self.log_view.setFont(QFont(MONO_FONT, 10)) # logs_tab.py
```

`QFont()` accepts a single family name string. Passing a CSS comma-separated list causes Qt to search for a font literally named `'"Cascadia Code", "Consolas"'` — which doesn't exist. The log view silently falls back to the system default font.

**Fix:**
```python
# styles.py
MONO_FONT = "Cascadia Code"
MONO_FONT_FALLBACK = "Consolas"

# logs_tab.py
from ui.styles import MONO_FONT, MONO_FONT_FALLBACK
db = QFontDatabase()
family = MONO_FONT if db.families().__contains__(MONO_FONT) else MONO_FONT_FALLBACK
self.log_view.setFont(QFont(family, 10))
```

Or simply:
```python
self.log_view.setFont(QFont("Consolas", 10))
```

---

### B3 — `_normalize()` Accepts `stack_root` But Never Uses It

**File:** `core/status_reader.py:72`

```python
def _normalize(data: dict, stack_root: str) -> dict:
```

`stack_root` is passed in from `get_status()` but is never referenced inside `_normalize()`. Dead parameter that pollutes every call site. If someone reads this signature they assume the path matters.

**Fix:** Remove the parameter from both the definition and the call:
```python
def _normalize(data: dict) -> dict:
```

---

## 🟠 Missed Security Fix (from previous audit)

---

### S1 — `_scan_and_import()` Still Writes `admin_pass` to `sites.json`

**File:** `ui/tabs/websites_tab.py:162–174`

The previous fix stripped `admin_pass` in `cms_install_dialog.py`, but auto-detected/imported sites bypass that path entirely:

```python
save_site({
    "folder": p.name,
    ...
    "admin_pass": "admin123",   # ← still here, written directly
    ...
})
```

Every folder that is auto-scanned and imported gets `admin_pass: "admin123"` written to `sites.json`.

**Fix:** Remove `admin_pass` from the `save_site()` call in `_scan_and_import()`:
```python
save_site({
    "folder": p.name,
    "app_id": app_id,
    "app_name": app_name,
    "admin_user": "admin",
    # no admin_pass
    "site_title": p.name.replace("_", " ").title(),
    "php_folder": "php",
    "php_version": "PHP 8.2 (Default)",
    "installed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
})
```

---

## 🟡 Dead / Unused Code

---

### D1 — `LOG_PATHS` Dict is Never Used

**File:** `core/log_reader.py:3–7`

```python
LOG_PATHS = {
    "apache": ("Apache", ["apache/logs/error_log", "apache/logs/access.log"]),
    ...
}
```

`get_log()` uses `LOG_PATHS_FLAT`. `get_log_sources()` uses `LOG_PATHS_FLAT`. Nothing in the codebase imports or reads `LOG_PATHS`. Dead export.

**Fix:** Delete the `LOG_PATHS` dict (lines 3–7).

---

### D2 — `FONT_FAMILY` Constant is Never Used

**File:** `ui/styles.py:4`

```python
FONT_FAMILY = '"Segoe UI"'
```

Not imported anywhere, not referenced anywhere in the codebase. Dead constant.

**Fix:** Delete the line.

---

### D3 — `_THEME_PATH` is Never Used

**File:** `ui/styles.py:7`

```python
_THEME_PATH = Path(__file__).with_name("theme.qss")
```

`build_stylesheet()` builds its own path dynamically using `f"theme_{theme}.qss"`. `_THEME_PATH` points to a non-theme-specific `theme.qss` that doesn't exist and is never read.

**Fix:** Delete the line.

---

### D4 — `render_icons.py` Builds Multi-Size List But Only Uses Last Frame

**File:** `render_icons.py:37–57`

```python
sizes = [16, 32, 48, 64, 128, 256]
pixmaps = []
for size in sizes:
    pixmap = QPixmap(size, size)
    ...
    pixmaps.append(pixmap)

pixmaps[-1].save(png_path, "PNG")   # only 256px used
pixmaps[-1].save(ico_path, "ICO")   # only 256px saved, ICO loses multi-size
```

The ICO format supports embedding multiple sizes (16/32/48) for sharp display at any scale. Saving only the 256px frame means the ICO is oversized and won't display sharply at small sizes in taskbars or file explorers.

**Fix:** Use `QIcon` to build a proper multi-resolution ICO, or save each size and combine.

---

### D5 — `get_mysql_connection()` Always Returns an Object — `if conn:` is Always True

**File:** `ui/tabs/websites_tab.py:521–522` · `core/installer.py:53–54`

```python
conn = get_mysql_connection(str(stack_root), s.get("mysql_port", 3306))
if conn:   # always True — SubprocessSQLConnection is always truthy
```

`get_mysql_connection()` always returns a `SubprocessSQLConnection` instance. It never returns `None` or `False`. The `if conn:` guard is misleading and does nothing.

**Fix:** Remove the guard; errors will be caught by the surrounding `try/except`:
```python
try:
    conn = get_mysql_connection(str(stack_root), s.get("mysql_port", 3306))
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS `{self.site.get('db_name', folder)}`;")
except Exception as e:
    print(f"DB drop error: {e}")
```

---

### D6 — `cur.close()` then `conn.close()` — Double-Close, Both No-ops

**File:** `ui/tabs/websites_tab.py:524–525`

```python
cur = conn.cursor()       # cursor() returns self (conn)
cur.execute(...)
cur.close(); conn.close() # close() is a no-op — called twice on same object
```

`SubprocessSQLConnection.cursor()` returns `self`, so `cur` and `conn` are the same object. Calling `.close()` on both is redundant (and `.close()` is a no-op anyway). The variable `cur` exists only to mimic a DB-API pattern that isn't actually implemented.

**Fix:** Simplify:
```python
conn = get_mysql_connection(str(stack_root), s.get("mysql_port", 3306))
conn.execute(f"DROP DATABASE IF EXISTS `{self.site.get('db_name', folder)}`;")
```

---

## 🔵 Code Smells / Duplicates

---

### CS1 — `density_button_height(density)` Ignores Its Own Parameter

**File:** `ui/styles.py:11–15`

```python
def density_button_height(density: str) -> int:
    try:
        h = int(load_settings().get("btn_height", 25))
        return h if 24 <= h <= 56 else 25
    except Exception:
        return 25
```

The `density` parameter is declared but never read. Every caller passes a density value expecting it to influence the result, but it doesn't. The function always reads `btn_height` from settings. This is misleading for every call site.

**Fix:** Either remove the parameter or actually use it:
```python
def density_button_height(density: str) -> int:
    base = 25 if density == "compact" else 30
    try:
        h = int(load_settings().get("btn_height", base))
        return h if 24 <= h <= 56 else base
    except Exception:
        return base
```

---

### CS2 — Module-Level Imports Buried Inside Class Body (`cms_install_dialog.py`)

**File:** `ui/dialogs/cms_install_dialog.py:45–46`

```python
class _MySQLStartWorker(QThread):
    ...
    # end of class

from core.config import load_settings, save_site      # ← here, at module scope
from core.installer import discover_php_versions       # ← but between two class defs
```

These imports are at module scope but positioned between the end of `_MySQLStartWorker` and the start of `CMSInstallDialog`. This is valid Python but extremely confusing — it looks like they're part of the class body at first glance.

**Fix:** Move both imports to the top of the file with the other imports.

---

### CS3 — `_flags()` Logic Duplicated in Two Files

**Files:** `core/service_manager.py:34–37` · `core/cms_installer.py:56–59`

```python
# service_manager.py
def _flags():
    f = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        f |= subprocess.CREATE_NO_WINDOW
    return f

# cms_installer.py
def _flags(self) -> int:
    f = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        f |= subprocess.CREATE_NO_WINDOW
    return f
```

Identical logic copied verbatim. If this ever needs to change (e.g. add another flag), it must be changed in two places.

**Fix:** Move to a shared utility, e.g. `core/utils.py`:
```python
def no_window_flags() -> int:
    return subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
```

---

### CS4 — `_settings()` Method in `CMSInstallWorker` Calls `load_settings()` on Every Operation

**File:** `core/cms_installer.py:62–64`

```python
def _settings(self) -> dict:
    from core.config import load_settings
    return load_settings()
```

`_settings()` is called 4–5 times per installation (`_install_wordpress`, `_assert_mysql_running`, `_create_database`, etc.) — each call reads and parses the JSON file from disk again. Settings don't change during an install.

**Fix:** Load once at the start of each `_install_*` method, or load in `run()` and pass down:
```python
def run(self):
    self._cached_settings = load_settings()   # load once
    ...
```

---

*End of code quality audit. 3 bugs, 1 missed security fix, 6 dead-code items, 4 code smells.*
