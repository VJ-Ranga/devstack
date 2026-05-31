# GitHub Copilot Instructions — DevStack Manager

Full project context is in `AGENTS.md` at the repo root.

## Project summary
Windows-only portable local web stack controller. Python/PySide6 desktop app + PHP web portal.
Default stack: Nginx + PHP-CGI (3 processes) + MariaDB. Apache is optional and does not auto-start.

## Critical patterns

### subprocess — always suppress console window
```python
from core.utils import no_window_flags
subprocess.Popen([exe] + args, creationflags=no_window_flags())
```

### Zip extraction — always use the shared safe helper
```python
from core.utils import safe_extractall
safe_extractall(zip_ref, target_dir)  # blocks Zip Slip attacks
```

### QThread worker — never null in finished signal
```python
def _on_done(self, result):
    pass  # DO NOT null self._worker here — crashes with libshiboken error

def _run(self):
    if self._worker and self._worker.isRunning():
        return
    self._worker = None   # safe: isRunning() returned False
    self._worker = MyWorker(...)
    self._worker.start()
```

### Settings — load once per worker run
```python
def run(self):
    self._cached_settings = load_settings()  # once, not per sub-method
```

## Never do
- `zipfile.ZipFile.extractall()` directly — use `safe_extractall()` from `core/utils.py`
- Store `admin_pass` in sites.json or any config
- `QFont('"Font A", "Font B"')` — QFont takes ONE family name
- Hardcode absolute paths in nginx/apache/mysql configs — use `DEVSTACK_ROOT` placeholder
- Add service start/stop controls to the web dashboard — it is read-only
- `--allow-root` in WP-CLI commands, or `shell=True` in subprocess
- Null a QThread worker inside its `finished` signal

## UI target
Windows 11 utility style. Calm, flat, no decorative elements.
See `UI-RULES.md` for full rules.
