# DevStack Security & Code Quality Audit

**Auditor:** Senior-level review  
**Date:** 2026-05-29  
**Scope:** Full codebase — Python app, PHP dashboard, Nginx/PHP config  

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 3 |
| 🟡 Medium | 4 |
| 🔵 Low / Info | 4 |

---

## 🔴 Critical

---

### C1 — Zip Slip Path Traversal (Remote Code Write)

**Files:** `devstack-app/core/php_manager.py:75–76` · `devstack-app/core/cms_installer.py:310, 350, 416`

`zipfile.ZipFile.extractall()` is called with no path sanitization on any zip entry names. A malicious archive (or a compromised CDN response) can contain entries like:

```
../../apache/conf/httpd.conf
../../mysql/devstack-grants.sql
```

This overwrites arbitrary files in the stack outside the target folder. Since the app downloads from public URLs (php.net, wordpress.org, drupal.org, github.com) without any hash check, a MITM or compromised CDN can serve a crafted zip.

**Fix — sanitize every member before extracting:**

```python
import os

def safe_extractall(zip_ref, target_dir):
    target_dir = os.path.realpath(target_dir)
    for member in zip_ref.infolist():
        member_path = os.path.realpath(os.path.join(target_dir, member.filename))
        if not member_path.startswith(target_dir + os.sep):
            raise RuntimeError(f"Zip Slip blocked: {member.filename}")
        zip_ref.extract(member, target_dir)
```

Apply this helper in every location that calls `zip_ref.extractall(...)`.

---

### C2 — No Download Integrity Verification

**Files:** `devstack-app/core/php_manager.py:49–70` · `devstack-app/core/cms_installer.py:141–165`

PHP binaries are downloaded from `https://windows.php.net/downloads/releases/` and extracted directly. There is **no SHA256 / MD5 hash check** against the official checksums that php.net publishes alongside each release. If the download is tampered with (MITM, DNS spoofing, compromised mirror), a malicious binary is silently installed and executed.

**Fix:**

1. Add a `"sha256"` key to each entry in `STABLE_PHP_VERSIONS`.
2. After download, verify `hashlib.sha256(zip_bytes).hexdigest() == expected` before extracting.
3. For CMS downloads (WordPress, Drupal) fetch the checksum file from the official server separately and verify before extraction.

---

## 🟠 High

---

### H1 — PHP FastCGI Stops Randomly (Root Cause)

**Files:** `devstack-app/core/service_manager.py:235–239` · `devstack-template/nginx/conf/nginx.conf:46`

Two bugs combine to cause the "PHP stops sometimes" issue you reported:

**Bug 1 — `PHP_FCGI_CHILDREN` does not work on Windows.**  
`PHP_FCGI_CHILDREN=5` is a Linux-only env var. On Windows, `php-cgi.exe` ignores it entirely. You are running a single php-cgi process with no children. When that one process encounters a fatal error or an unhandled exception in user code, the entire FastCGI listener exits and Nginx starts returning 502 errors.

**Bug 2 — No watchdog / auto-restart.**  
`_wait_for()` only checks that the process started within `timeout` seconds. Once the process exits later (after minutes or hours), nothing detects it or relaunches it.

**Fix (two parts):**

```python
# service_manager.py — remove the non-working env var, spawn N copies instead
if k == "php":
    env = _os.environ.copy()
    env["PHP_FCGI_MAX_REQUESTS"] = "0"
    # Spawn 5 independent php-cgi processes on the same port (Windows approach)
    for _ in range(5):
        subprocess.Popen([str(exe)] + args, cwd=wd, creationflags=flags, env=env)
```

And in nginx.conf, increase the FastCGI connect timeout so a slow restart doesn't immediately 502:

```nginx
fastcgi_connect_timeout  30s;   # was 5s — too short if php-cgi is slow to bind
fastcgi_read_timeout    120s;   # increase for long-running scripts
```

Also consider adding a simple watchdog QTimer in the UI that calls `_is_running("php-cgi.exe")` every 30 s and restarts if not running.

---

### H2 — CSRF on Dashboard Service Controls

**File:** `devstack-template/htdocs/dashboard/index.php:41–59, 568–573`

The POST forms that start/stop/restart services have **no CSRF token**. Any webpage the user visits can silently POST to `http://localhost/dashboard/` and stop all DevStack services or restart them. This is a localhost app but browsers allow cross-origin POSTs to localhost by default.

**Fix:**

```php
// On page load — generate token and store in session
session_start();
if (empty($_SESSION['csrf'])) {
    $_SESSION['csrf'] = bin2hex(random_bytes(32));
}

// Validate on POST
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!hash_equals($_SESSION['csrf'], $_POST['csrf_token'] ?? '')) {
        http_response_code(403);
        exit('Forbidden');
    }
}
```

Add `<input type="hidden" name="csrf_token" value="<?php echo $_SESSION['csrf']; ?>">` to every form.

---

### H3 — Plaintext Credentials Stored in sites.json

**File:** `devstack-app/config/sites.json:8, 20`

WordPress admin passwords (e.g. `"admin_pass": "admin123"`) are saved in plaintext in `sites.json` on disk. If this file is accidentally committed to a public repo or synced to cloud storage, credentials are exposed. The fact that the default password is `admin123` compounds the risk.

**Fix:**

- Do not persist `admin_pass` in `sites.json` at all after installation is complete. The password is only needed at install time.
- At minimum, add `sites.json` to `.gitignore`.
- Force users to choose a non-default password in the CMS install dialog (reject `admin`, `admin123`, `password`).

---

## 🟡 Medium

---

### M1 — `--allow-root` Always Passed to WP-CLI

**File:** `devstack-app/core/cms_installer.py:198`

```python
cmd = [str(php_exe), "-d", "phar.readonly=0", str(wp_cli)] + args + ["--allow-root"]
```

`--allow-root` is appended unconditionally. This flag suppresses WP-CLI's safety check that prevents running as the system root user. It is unnecessary on Windows where there is no concept of UID 0, and it masks the warning if someone ever runs this on Linux/WSL as root (which would be a real risk). Remove it.

---

### M2 — MariaDB Root Has No Password

**File:** `devstack-app/core/cms_installer.py:265` · `devstack-app/core/service_manager.py:28`

```python
"--dbpass=",      # wp-config create: empty root password
"-e", "SELECT 1;" # mysql connect check: no -p flag = no password
```

Root credentials with no password mean any process running on the machine can connect to MariaDB on port 3306 with full privileges. While this is a local dev stack, it is still exploitable by malicious local apps or scripts.

**Fix:** Set a strong root password in `devstack-grants.sql` during first-run init and store it in `app-settings.json` (not `sites.json`). Pass `--password=...` in all mysql calls.

---

### M3 — `runCmd()` Ignores Exit Code — Silent Failures

**File:** `devstack-template/htdocs/dashboard/index.php:11–13`

```php
function runCmd(string $command): string {
    $out = shell_exec('cmd /c ' . escapeshellarg($command) . ' 2>&1');
    return is_string($out) ? trim($out) : '';
}
```

The return value of `shell_exec` is only the output string. If the PowerShell command fails (script not found, access denied, service error), `$notice` is still set to "All services started successfully." — a false confirmation shown to the user.

**Fix:** Switch to `exec()` or `proc_open()` and capture the exit code:

```php
function runCmd(string $command): array {
    exec('cmd /c ' . escapeshellarg($command) . ' 2>&1', $output, $code);
    return ['output' => implode("\n", $output), 'success' => $code === 0];
}
```

---

### M4 — Nginx Error Log Is Commented Out

**File:** `devstack-template/nginx/conf/nginx.conf:5–7`

```nginx
#error_log  logs/error.log;
#error_log  logs/error.log  notice;
#error_log  logs/error.log  info;
```

All three `error_log` directives are commented out. Nginx defaults to logging errors to `stderr` only, which is discarded when run as a background process. This means **PHP 502/504 errors are silently lost** — making PHP stopping hard to diagnose.

**Fix:** Uncomment the first line:

```nginx
error_log  logs/error.log  warn;
```

---

## 🔵 Low / Info

---

### L1 — nginx.conf `client_max_body_size` Set to 512 MB in Template

**File:** `devstack-template/nginx/conf/nginx.conf:21`

The template ships with `client_max_body_size 512M`. This is overridden by settings at runtime, but the on-disk template value is extremely large for a default. If someone uses the nginx.conf directly without running the manager, they get a 512 MB upload limit with no warning.

**Recommendation:** Lower the template default to `128M` to match the app setting default.

---

### L2 — PHP Download URLs Point to Specific Archived Versions

**File:** `devstack-app/core/php_manager.py:8–15`

Several entries (PHP 8.3.7, 8.2.19, 8.1.28, 8.0.30, 7.4.33) point to `/releases/archives/` — these are known-old patch versions with published CVEs. Offering them in the UI without a security warning may lead users to install PHP with known vulnerabilities.

**Recommendation:** Either bump to the latest patch for each minor version, or add a UI warning: "⚠️ PHP 7.4 is end-of-life and has unpatched security vulnerabilities."

---

### L3 — Crash Log Written Outside the App Directory

**File:** `devstack-app/main.py:29–31`

```python
app_root = Path(__file__).resolve().parents[1]
log_dir = app_root / "logs"
```

`parents[1]` goes one level above `devstack-app/`, landing in the repo root `portable-stack-plan/logs/`. The `logs/` directory is already showing as untracked in git (`?? logs/`). If this directory ever gets committed by mistake, crash logs (which include full Python tracebacks and file paths) would be published.

**Fix:** Add `logs/` to `.gitignore` immediately. Better yet, write crash logs to `%APPDATA%\DevStack\logs\` instead of inside the repo.

---

### L4 — `_sync_*_config()` Functions Silently Swallow Write Errors

**Files:** `devstack-app/core/service_manager.py:121, 153, 168`

```python
except Exception as e:
    print(f"Error syncing Nginx config: {e}")
```

Config sync failures (disk full, file locked, permission denied) are printed to console only and the service is started anyway with a stale/wrong config. This can cause confusing failures where the service starts on the wrong port.

**Fix:** Return a bool or raise, and propagate the error up to the caller so the UI can display it before attempting to start services.

---

## PHP Stopping — Quick Checklist

Given the analysis in **H1**, here is a step-by-step checklist to fix PHP stopping:

- [ ] Remove `PHP_FCGI_CHILDREN=5` from the env block — it does nothing on Windows
- [ ] Spawn 3–5 independent `php-cgi.exe` processes instead (loop in `start()`)
- [ ] Set `fastcgi_connect_timeout 30s;` in nginx.conf (from 5s)
- [ ] Uncomment `error_log logs/error.log warn;` in nginx.conf so you can see 502 causes
- [ ] Add a QTimer watchdog in the Overview tab that checks `_is_running("php-cgi.exe")` every 30 s and auto-restarts if dead
- [ ] Check `nginx/logs/error.log` after PHP stops for the actual error message

---

*End of audit. Total: 2 critical, 3 high, 4 medium, 4 low findings.*
