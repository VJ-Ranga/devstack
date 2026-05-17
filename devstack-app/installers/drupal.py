import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

class DrupalInstaller:
    meta = {
        "id": "drupal",
        "name": "Drupal",
        "desc": "An open-source CMS for building highly custom, enterprise websites.",
        "icon": "💧",
        "category": "CMS & Enterprise"
    }

    @staticmethod
    def get_inputs():
        return [
            {"key": "site_name", "label": "Site Folder Name", "type": "text", "default": "dev_drupal"},
            {"key": "db_name", "label": "Database Name", "type": "text", "default": "dev_drupal"},
            {"key": "admin_user", "label": "Admin Username", "type": "text", "default": "admin"},
            {"key": "admin_pass", "label": "Admin Password", "type": "password", "default": "admin123"},
        ]

    @classmethod
    def install(cls, target_dir: Path, params: dict, mysql_conn, progress_callback):
        # 1. Download official Drupal release
        zip_path = target_dir.parent / "drupal_latest.zip"
        progress_callback("Downloading official Drupal package...", 20)
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request("https://www.drupal.org/download-latest/zip", headers=headers)
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

        # 2. Extract files
        progress_callback("Extracting core Drupal files...", 50)
        os.makedirs(target_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Drupal zip extracts to a parent folder named e.g., 'drupal-10.x.x'
            temp_extract = target_dir.parent / "temp_drupal_extract"
            os.makedirs(temp_extract, exist_ok=True)
            zip_ref.extractall(temp_extract)
            
            # Find the extracted folder
            extracted_dirs = [d for d in temp_extract.iterdir() if d.is_dir()]
            if extracted_dirs:
                src_drupal = extracted_dirs[0]
                for item in src_drupal.iterdir():
                    dest_item = target_dir / item.name
                    if dest_item.exists():
                        if dest_item.is_dir():
                            shutil.rmtree(dest_item)
                        else:
                            os.remove(dest_item)
                    shutil.move(str(item), str(target_dir))
            
            shutil.rmtree(temp_extract)

        if zip_path.exists():
            os.remove(zip_path)

        # 3. Connect to database and create it
        progress_callback("Creating database in MariaDB...", 75)
        cursor = mysql_conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{params['db_name']}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()

        # 4. Set write permissions to settings folder for installation wizard
        progress_callback("Setting up permissions...", 95)
        settings_dir = target_dir / "sites" / "default"
        if settings_dir.exists():
            # Copy default.settings.php to settings.php
            default_settings = settings_dir / "default.settings.php"
            target_settings = settings_dir / "settings.php"
            if default_settings.exists() and not target_settings.exists():
                shutil.copy(str(default_settings), str(target_settings))
                try:
                    os.chmod(str(target_settings), 0o666)
                except Exception:
                    pass

        progress_callback("Drupal prepared successfully! Complete setup via browser.", 100)
