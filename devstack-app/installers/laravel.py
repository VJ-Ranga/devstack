import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

class LaravelInstaller:
    meta = {
        "id": "laravel",
        "name": "Laravel Framework",
        "desc": "The most elegant PHP web application framework with expressive, beautiful syntax.",
        "icon": "🌶️",
        "category": "MVC Framework"
    }

    @staticmethod
    def get_inputs():
        return [
            {"key": "site_name", "label": "Site Folder Name", "type": "text", "default": "dev_laravel"},
            {"key": "db_host", "label": "Database Host", "type": "text", "default": "127.0.0.1"},
            {"key": "db_port", "label": "Database Port", "type": "text", "default": "3306"},
            {"key": "db_name", "label": "Database Name", "type": "text", "default": "dev_laravel"},
        ]

    @classmethod
    def install(cls, target_dir: Path, params: dict, mysql_conn, progress_callback, log_callback):
        # 1. Download official Laravel release skeleton zip
        zip_path = target_dir.parent / "laravel_skeleton.zip"
        progress_callback("Downloading Laravel package...", 20)
        log_callback("Downloading Laravel framework release skeleton from GitHub...")
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request("https://github.com/laravel/laravel/archive/refs/heads/11.x.zip", headers=headers)
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        
        log_callback(f"Successfully downloaded Laravel archive to {zip_path.name}")

        # 2. Extract files
        progress_callback("Extracting core files...", 50)
        log_callback("Extracting framework skeleton contents...")
        os.makedirs(target_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract into temporary folder in parent
            temp_extract = target_dir.parent / "temp_laravel_extract"
            os.makedirs(temp_extract, exist_ok=True)
            zip_ref.extractall(temp_extract)
            
            # Laravel zip extracts to 'laravel-11.x/' inside the zip. Move contents to target_dir/
            src_wp = temp_extract / "laravel-11.x"
            if not src_wp.exists():
                # Fallback in case archive root name differs
                for folder in temp_extract.iterdir():
                    if folder.is_dir():
                        src_wp = folder
                        break
            
            if src_wp.exists():
                file_count = 0
                for item in src_wp.iterdir():
                    dest_item = target_dir / item.name
                    if dest_item.exists():
                        if dest_item.is_dir():
                            shutil.rmtree(dest_item)
                        else:
                            os.remove(dest_item)
                    shutil.move(str(item), str(target_dir))
                    file_count += 1
                log_callback(f"Extracted and configured {file_count} framework core files.")
            
            shutil.rmtree(temp_extract)

        if zip_path.exists():
            os.remove(zip_path)
            log_callback("Cleaned up temporary archive cache.")

        # 3. Create MariaDB database
        progress_callback("Creating database...", 75)
        db_name = params.get("db_name", "").strip()
        if db_name:
            log_callback(f"Initializing database `{db_name}`...")
            cursor = mysql_conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.close()
            log_callback(f"Database `{db_name}` is ready.")

        # 4. Generate local .env file
        progress_callback("Configuring .env settings...", 90)
        env_example = target_dir / ".env.example"
        env_file = target_dir / ".env"
        
        if env_example.exists():
            log_callback("Found .env.example. Setting up local environment configurations...")
            content = env_example.read_text(encoding="utf-8")
            
            # Substitute local DB credentials
            db_host = params.get("db_host", "127.0.0.1").strip()
            db_port = params.get("db_port", "3306").strip()
            
            # Replace lines in env block
            lines = []
            for line in content.splitlines():
                if line.startswith("DB_HOST="):
                    line = f"DB_HOST={db_host}"
                elif line.startswith("DB_PORT="):
                    line = f"DB_PORT={db_port}"
                elif line.startswith("DB_DATABASE="):
                    line = f"DB_DATABASE={db_name}"
                elif line.startswith("DB_USERNAME="):
                    line = "DB_USERNAME=root"
                elif line.startswith("DB_PASSWORD="):
                    line = "DB_PASSWORD="
                lines.append(line)
            
            env_file.write_text("\n".join(lines), encoding="utf-8")
            log_callback(".env file generated with local database configurations.")

        progress_callback("Laravel installed successfully!", 100)
        log_callback(">>> One-Click Laravel Installation Completed Successfully!")
        log_callback("Note: Access your new Laravel site public folder via browser at /dev_laravel/public/")
