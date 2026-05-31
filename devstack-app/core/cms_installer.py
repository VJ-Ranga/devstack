import re
import shutil
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.config import load_settings
from core.utils import no_window_flags, safe_extractall as _safe_extractall

# Cache zips for this many days before re-downloading
_CACHE_MAX_AGE_DAYS = 7

CMS_OPTIONS = [
    {"id": "custom_php", "label": "Plain PHP"},
    {"id": "wordpress",  "label": "WordPress"},
    {"id": "drupal",     "label": "Drupal"},
    {"id": "laravel",    "label": "Laravel"},
]

CMS_NOTES = {
    "custom_php": "Creates a starter index.php project. No database or extra setup required.",
    "wordpress":  "Downloads WordPress via WP-CLI and runs a full silent install. MariaDB must be running first.",
    "drupal":     "Downloads Drupal and creates the database. Complete the setup via the browser wizard after install. MariaDB must be running first.",
    "laravel":    "Downloads the Laravel skeleton from GitHub. After creation you must run 'composer install' inside the project folder to install PHP dependencies before the site will work.",
}


class CMSInstallWorker(QThread):
    progress    = Signal(str, int)
    log_emitted = Signal(str)
    finished    = Signal(bool, str)

    def __init__(self, stack_root: str, site_config: dict):
        super().__init__()
        self.stack_root  = Path(stack_root)
        self.site_config = site_config

    def run(self):
        # Load settings once for the entire install — avoids repeated disk reads
        self._cached_settings = load_settings()
        app_id = self.site_config.get("app_id", "custom_php")
        try:
            if app_id == "wordpress":
                self._install_wordpress()
            elif app_id == "drupal":
                self._install_drupal()
            elif app_id == "laravel":
                self._install_laravel()
            else:
                self._install_plain_php()
        except Exception as e:
            self.log_emitted.emit(f"[FATAL ERROR] {e}")
            self.finished.emit(False, str(e))

    # ── internal helpers ───────────────────────────────────────────────────

    def _settings(self) -> dict:
        return self._cached_settings

    def _php_exe(self) -> Path:
        s = self._settings()
        active = s.get("active_php_folder", "php")
        return self.stack_root / active / "php.exe"

    def _wp_cli(self) -> Path:
        return self.stack_root / "tools" / "wp-cli.phar"

    def _assert_mysql_running(self) -> None:
        """Raise immediately if MariaDB is not reachable — call before any download."""
        s = self._settings()
        mysql_port = int(s.get("mysql_port", 3306))
        mysql_exe  = self.stack_root / "mysql" / "bin" / "mysql.exe"
        if not mysql_exe.exists():
            raise FileNotFoundError(
                f"mysql.exe not found at {mysql_exe}.\n"
                "Make sure the DevStack template folder is correct in Settings."
            )
        self.log_emitted.emit("Checking MariaDB connection...")
        result = subprocess.run(
            [
                str(mysql_exe),
                "--host=127.0.0.1", f"--port={mysql_port}",
                "--ssl=0", "-u", "root",
                "--connect-timeout=4",
                "-e", "SELECT 1;",
            ],
            capture_output=True, text=True, timeout=8,
            creationflags=no_window_flags(),
        )
        if result.returncode != 0:
            raise RuntimeError(
                "MariaDB is not running or not reachable.\n\n"
                "Please start MariaDB first:\n"
                "  Go to the Control or Services tab and start the stack (or MariaDB individually),\n"
                "  then try the installation again."
            )
        self.log_emitted.emit("MariaDB connection OK.")

    def _create_database(self, db_name: str) -> None:
        s = self._settings()
        mysql_port = int(s.get("mysql_port", 3306))
        mysql_exe  = self.stack_root / "mysql" / "bin" / "mysql.exe"
        if not mysql_exe.exists():
            raise FileNotFoundError(f"mysql.exe not found at {mysql_exe}")
        self.log_emitted.emit(f"Creating database `{db_name}`...")
        result = subprocess.run(
            [
                str(mysql_exe),
                "--host=127.0.0.1", f"--port={mysql_port}",
                "--ssl=0", "-u", "root",
                "-e",
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
            ],
            capture_output=True, text=True, timeout=15,
            creationflags=no_window_flags(),
        )
        if result.returncode != 0:
            raise RuntimeError(f"Database creation failed:\n{result.stderr or result.stdout}")
        self.log_emitted.emit(f"Database `{db_name}` ready.")

    def _cache_dir(self) -> Path:
        """Returns (and creates) the DevStack download cache directory."""
        d = self.stack_root / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _is_cache_fresh(self, path: Path) -> bool:
        """True if the cached file exists and is younger than _CACHE_MAX_AGE_DAYS."""
        if not path.exists():
            return False
        age_days = (time.time() - path.stat().st_mtime) / 86400
        return age_days < _CACHE_MAX_AGE_DAYS

    def _download_zip(self, url: str, dest: Path, label: str = "file") -> None:
        self.log_emitted.emit(f"Downloading {label}...")
        self.log_emitted.emit(f"URL: {url}")
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 DevStack-Manager/1.0"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            total      = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_pct   = -10
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded / total * 100)
                        if pct >= last_pct + 10:
                            self.log_emitted.emit(
                                f"  {downloaded // 1024} KB / {total // 1024} KB ({pct}%)"
                            )
                            last_pct = pct
        self.log_emitted.emit("Download complete.")

    def _cached_download_zip(
        self, url: str, cache_name: str, dest: Path, label: str = "file"
    ) -> None:
        """
        Download `url` to `dest`, using a cached copy in stack_root/cache/<cache_name>
        if it is younger than _CACHE_MAX_AGE_DAYS days.  On a fresh download the cache
        is updated automatically.
        """
        cached = self._cache_dir() / cache_name
        if self._is_cache_fresh(cached):
            self.log_emitted.emit(
                f"Using cached {label} ({cached.stat().st_size // (1024*1024)} MB, "
                f"< {_CACHE_MAX_AGE_DAYS} days old) — skipping download."
            )
            shutil.copy2(str(cached), str(dest))
        else:
            if cached.exists():
                self.log_emitted.emit(
                    f"Cached {label} is older than {_CACHE_MAX_AGE_DAYS} days — re-downloading."
                )
            self._download_zip(url, dest, label)
            # Update the cache with the freshly downloaded file
            try:
                shutil.copy2(str(dest), str(cached))
                self.log_emitted.emit(f"Cache updated: cache/{cache_name}")
            except Exception as e:
                self.log_emitted.emit(f"[WARNING] Could not update cache: {e}")

    def _run_wpcli(self, args: list, timeout: int = 120) -> subprocess.CompletedProcess:
        php_exe = self._php_exe()
        wp_cli  = self._wp_cli()
        cmd = [str(php_exe), "-d", "phar.readonly=0", str(wp_cli)] + args
        self.log_emitted.emit("$ wp " + " ".join(args))
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=timeout,
            creationflags=no_window_flags(),
        )
        out = (result.stdout or result.stderr or "").strip()
        if out:
            self.log_emitted.emit(out)
        return result

    # ── CMS installers ─────────────────────────────────────────────────────

    def _install_wordpress(self) -> None:
        s          = self._settings()
        mysql_port = int(s.get("mysql_port", 3306))
        nginx_port = int(s.get("nginx_port", 80))
        folder     = self.site_config["folder"]
        title      = self.site_config.get("site_title") or folder.replace("_", " ").title()
        admin_user = self.site_config.get("admin_user", "admin")
        admin_pass = self.site_config.get("admin_pass", "admin123")
        admin_email= self.site_config.get("admin_email", "admin@localhost.local")
        db_name    = re.sub(r"[^a-zA-Z0-9_]", "_", folder)
        target     = self.stack_root / "htdocs" / folder
        base_url   = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"

        php_exe = self._php_exe()
        wp_cli  = self._wp_cli()
        if not php_exe.exists():
            raise FileNotFoundError(f"PHP executable not found: {php_exe}")
        if not wp_cli.exists():
            raise FileNotFoundError(
                f"WP-CLI not found at {wp_cli}. "
                "Ensure wp-cli.phar is in devstack-template/tools/"
            )

        # Step 1 — download core
        self.progress.emit("Downloading WordPress core files...", 10)
        self.log_emitted.emit(">>> Step 1 of 4 — Downloading WordPress core via WP-CLI")
        target.mkdir(parents=True, exist_ok=True)
        r = self._run_wpcli(
            ["core", "download", f"--path={target}", "--locale=en_US"],
            timeout=180,
        )
        if r.returncode != 0:
            out_lower = (r.stdout + r.stderr).lower()
            if "already" in out_lower:
                self.log_emitted.emit("WordPress files already present, continuing...")
            else:
                self.log_emitted.emit("[WARNING] WP-CLI download failed — trying direct download as fallback")
                self._wordpress_direct_download(target)

        # Step 2 — create database
        self.progress.emit("Creating database...", 35)
        self.log_emitted.emit(">>> Step 2 of 4 — Creating MySQL database")
        self._create_database(db_name)

        # Step 3 — create wp-config.php
        self.progress.emit("Creating wp-config.php...", 52)
        self.log_emitted.emit(">>> Step 3 of 4 — Generating wp-config.php")
        db_host = f"127.0.0.1:{mysql_port}" if mysql_port != 3306 else "127.0.0.1"
        r = self._run_wpcli([
            "config", "create",
            f"--path={target}",
            f"--dbname={db_name}",
            "--dbuser=root",
            "--dbpass=",
            f"--dbhost={db_host}",
            "--force",
        ])
        if r.returncode != 0:
            raise RuntimeError(f"wp-config.php creation failed:\n{r.stderr or r.stdout}")

        # Step 4 — install
        self.progress.emit("Installing WordPress...", 70)
        self.log_emitted.emit(">>> Step 4 of 4 — Running WordPress silent install")
        r = self._run_wpcli([
            "core", "install",
            f"--path={target}",
            f"--url={base_url}/{folder}",
            f"--title={title}",
            f"--admin_user={admin_user}",
            f"--admin_password={admin_pass}",
            f"--admin_email={admin_email}",
            "--skip-email",
        ], timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"WordPress install failed:\n{r.stderr or r.stdout}")

        self.progress.emit("WordPress installed successfully!", 100)
        self.log_emitted.emit(">>> Installation complete!")
        self.finished.emit(
            True,
            f"WordPress installed successfully!\n\n"
            f"Site URL:     {base_url}/{folder}\n"
            f"Admin panel:  {base_url}/{folder}/wp-admin/\n"
            f"Username:     {admin_user}\n"
            f"Password:     {admin_pass}",
        )

    def _wordpress_direct_download(self, target: Path) -> None:
        zip_path    = self.stack_root / "_wp_tmp.zip"
        extract_dir = self.stack_root / "_wp_extract_tmp"
        try:
            self._cached_download_zip(
                "https://wordpress.org/latest.zip",
                "wordpress-latest.zip",
                zip_path,
                "WordPress",
            )
            self.log_emitted.emit("Extracting WordPress files...")
            with zipfile.ZipFile(str(zip_path), "r") as z:
                _safe_extractall(z, extract_dir)
            inner = extract_dir / "wordpress"
            if inner.exists():
                if target.exists():
                    shutil.rmtree(str(target))
                shutil.move(str(inner), str(target))
                self.log_emitted.emit("WordPress files extracted successfully.")
            else:
                raise RuntimeError("wordpress/ folder not found inside the downloaded archive.")
        finally:
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)
            if extract_dir.exists():
                shutil.rmtree(str(extract_dir), ignore_errors=True)

    def _install_drupal(self) -> None:
        s          = self._settings()
        nginx_port = int(s.get("nginx_port", 80))
        folder     = self.site_config["folder"]
        db_name    = re.sub(r"[^a-zA-Z0-9_]", "_", folder)
        target     = self.stack_root / "htdocs" / folder
        zip_path   = self.stack_root / "_drupal_tmp.zip"
        extract_dir= self.stack_root / "_drupal_extract_tmp"
        base_url   = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"

        try:
            # Step 1 — download
            self.progress.emit("Downloading Drupal...", 10)
            self.log_emitted.emit(">>> Step 1 of 3 — Downloading latest Drupal release")
            self._cached_download_zip(
                "https://www.drupal.org/download-latest/zip",
                "drupal-latest.zip",
                zip_path,
                "Drupal",
            )

            # Step 2 — extract
            self.progress.emit("Extracting Drupal...", 50)
            self.log_emitted.emit(">>> Step 2 of 3 — Extracting archive")
            with zipfile.ZipFile(str(zip_path), "r") as z:
                _safe_extractall(z, extract_dir)

            inner = next(
                (p for p in extract_dir.iterdir() if p.is_dir() and p.name.startswith("drupal")),
                None,
            )
            if not inner:
                raise RuntimeError(
                    "Could not locate drupal-X.X.X/ folder inside the downloaded archive."
                )

            if target.exists():
                shutil.rmtree(str(target))
            shutil.move(str(inner), str(target))
            self.log_emitted.emit(f"Drupal extracted to htdocs/{folder}")

        finally:
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)
            if extract_dir.exists():
                shutil.rmtree(str(extract_dir), ignore_errors=True)

        # Step 3 — create database
        self.progress.emit("Creating database...", 82)
        self.log_emitted.emit(">>> Step 3 of 3 — Creating MySQL database")
        self._create_database(db_name)

        self.progress.emit("Drupal ready — complete setup in browser!", 100)
        self.log_emitted.emit(">>> Files ready. Open the URL below in your browser to continue.")
        self.finished.emit(
            True,
            f"Drupal files are ready at htdocs/{folder}.\n"
            f"Database `{db_name}` has been created.\n\n"
            f"Open the link below to run the Drupal setup wizard:\n"
            f"  {base_url}/{folder}\n\n"
            f"Use these database credentials in the wizard:\n"
            f"  Database name:  {db_name}\n"
            f"  Database host:  127.0.0.1\n"
            f"  Username:       root\n"
            f"  Password:       (leave empty)",
        )

    def _install_laravel(self) -> None:
        s          = self._settings()
        nginx_port = int(s.get("nginx_port", 80))
        folder     = self.site_config["folder"]
        target     = self.stack_root / "htdocs" / folder
        zip_path   = self.stack_root / "_laravel_tmp.zip"
        extract_dir= self.stack_root / "_laravel_extract_tmp"
        base_url   = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"

        try:
            # Step 1 — download
            self.progress.emit("Downloading Laravel skeleton...", 10)
            self.log_emitted.emit(">>> Step 1 of 3 — Downloading Laravel from GitHub")
            self._cached_download_zip(
                "https://github.com/laravel/laravel/archive/refs/heads/master.zip",
                "laravel-latest.zip",
                zip_path,
                "Laravel",
            )

            # Step 2 — extract
            self.progress.emit("Extracting Laravel...", 55)
            self.log_emitted.emit(">>> Step 2 of 3 — Extracting archive")
            with zipfile.ZipFile(str(zip_path), "r") as z:
                _safe_extractall(z, extract_dir)

            inner = extract_dir / "laravel-master"
            if not inner.exists():
                inner = next(
                    (p for p in extract_dir.iterdir() if p.is_dir()), None
                )
            if not inner:
                raise RuntimeError(
                    "Could not locate Laravel folder inside the downloaded archive."
                )

            if target.exists():
                shutil.rmtree(str(target))
            shutil.move(str(inner), str(target))
            self.log_emitted.emit(f"Laravel extracted to htdocs/{folder}")

        finally:
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)
            if extract_dir.exists():
                shutil.rmtree(str(extract_dir), ignore_errors=True)

        # Step 3 — configure
        self.progress.emit("Configuring environment files...", 82)
        self.log_emitted.emit(">>> Step 3 of 3 — Preparing environment and storage directories")

        env_example = target / ".env.example"
        env_file    = target / ".env"
        if env_example.exists() and not env_file.exists():
            shutil.copy(str(env_example), str(env_file))
            self.log_emitted.emit("Created .env from .env.example")

        for d in [
            "storage/app/public",
            "storage/framework/sessions",
            "storage/framework/views",
            "storage/framework/cache/data",
            "storage/logs",
            "bootstrap/cache",
        ]:
            (target / d).mkdir(parents=True, exist_ok=True)
        self.log_emitted.emit("Storage directories created.")

        # Step 4 — auto-run composer install if available
        self.progress.emit("Running composer install...", 90)
        self.log_emitted.emit(">>> Step 4 — Checking for Composer...")
        composer_cmd = shutil.which("composer") or shutil.which("composer.phar")
        composer_done = False
        if composer_cmd:
            self.log_emitted.emit(f"Composer found: {composer_cmd}")
            self.log_emitted.emit("Running 'composer install --no-interaction --prefer-dist'...")
            comp_result = subprocess.run(
                [composer_cmd, "install", "--no-interaction", "--prefer-dist", "--optimize-autoloader"],
                cwd=str(target),
                capture_output=True, text=True, timeout=300,
                creationflags=no_window_flags(),
            )
            output = (comp_result.stdout or "") + (comp_result.stderr or "")
            if output.strip():
                self.log_emitted.emit(output.strip()[-3000:])
            if comp_result.returncode == 0:
                self.log_emitted.emit("Composer install completed successfully.")
                composer_done = True
            else:
                self.log_emitted.emit("[WARNING] Composer install failed — run it manually.")
        else:
            self.log_emitted.emit("[INFO] Composer not found in PATH — run 'composer install' manually.")

        self.progress.emit("Laravel ready!", 100)
        if composer_done:
            self.finished.emit(
                True,
                f"Laravel installed at htdocs/{folder}.\n\n"
                f"Composer dependencies installed automatically.\n\n"
                f"Visit:\n  {base_url}/{folder}/public/",
            )
        else:
            self.finished.emit(
                True,
                f"Laravel skeleton created at htdocs/{folder}.\n\n"
                f"⚠ Run 'composer install' inside the project folder before the site will work.\n\n"
                f"After that, visit:\n  {base_url}/{folder}/public/",
            )

    def _install_plain_php(self) -> None:
        s          = self._settings()
        nginx_port = int(s.get("nginx_port", 80))
        folder     = self.site_config["folder"]
        title      = self.site_config.get("site_title") or folder.replace("_", " ").title()
        target     = self.stack_root / "htdocs" / folder
        base_url   = f"http://localhost:{nginx_port}" if nginx_port != 80 else "http://localhost"

        target.mkdir(parents=True, exist_ok=True)
        (target / "index.php").write_text(
            f"<?php\n$title = {repr(title)};\n?>\n"
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "    <meta charset=\"UTF-8\">\n"
            "    <title><?php echo htmlspecialchars($title); ?></title>\n"
            "</head>\n<body>\n"
            "    <h1><?php echo htmlspecialchars($title); ?></h1>\n"
            "    <p>Project created successfully.</p>\n"
            "    <p>PHP Version: <?php echo PHP_VERSION; ?></p>\n"
            "</body>\n</html>\n",
            encoding="utf-8",
        )
        self.log_emitted.emit(f"PHP project created at htdocs/{folder}")
        self.progress.emit("Done!", 100)
        self.finished.emit(True, f"PHP project created.\nURL: {base_url}/{folder}")
