import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

class WordPressInstaller:
    meta = {
        "id": "wordpress",
        "name": "WordPress",
        "desc": "The world's most popular blogging, CMS, and website builder.",
        "icon": "🌐",
        "category": "CMS & Blogging"
    }

    @staticmethod
    def get_inputs():
        return [
            {"key": "site_name", "label": "Site Folder Name", "type": "text", "default": "dev_wordpress"},
            {"key": "db_host", "label": "Database Host", "type": "text", "default": "127.0.0.1"},
            {"key": "db_port", "label": "Database Port", "type": "text", "default": "3306"},
            {"key": "db_name", "label": "Database Name", "type": "text", "default": "dev_wordpress"},
            {"key": "admin_user", "label": "Admin Username", "type": "text", "default": "admin"},
            {"key": "admin_pass", "label": "Admin Password", "type": "password", "default": "admin123"},
        ]

    @classmethod
    def install(cls, target_dir: Path, params: dict, mysql_conn, progress_callback, log_callback):
        # 1. Download official WordPress release
        zip_path = target_dir.parent / "wordpress_latest.zip"
        progress_callback("Downloading official WordPress package...", 20)
        log_callback("Downloading latest WordPress release zip from wordpress.org...")
        
        # Use urllib to download the zip file
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request("https://wordpress.org/latest.zip", headers=headers)
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        
        log_callback(f"Successfully downloaded archive to {zip_path.name}")

        # 2. Extract files
        progress_callback("Extracting core WordPress files...", 50)
        log_callback("Extracting archive index contents...")
        os.makedirs(target_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract into temporary folder in parent
            temp_extract = target_dir.parent / "temp_wp_extract"
            os.makedirs(temp_extract, exist_ok=True)
            zip_ref.extractall(temp_extract)
            
            # Move files from temp_wp_extract/wordpress/ to target_dir/
            src_wp = temp_extract / "wordpress"
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
                log_callback(f"Extracted and configured {file_count} core system directories & files.")
            
            shutil.rmtree(temp_extract)

        if zip_path.exists():
            os.remove(zip_path)
            log_callback("Cleaned up temporary archive cache.")

        # 3. Connect to database and create it
        progress_callback("Creating database in MariaDB...", 75)
        db_name = params['db_name']
        log_callback(f"Requesting database initialization: `{db_name}`")
        cursor = mysql_conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        log_callback(f"Database `{db_name}` verified/created successfully.")

        # 4. Generate wp-config.php
        progress_callback("Configuring wp-config.php...", 90)
        sample_path = target_dir / "wp-config-sample.php"
        config_path = target_dir / "wp-config.php"
        
        if sample_path.exists():
            log_callback("Found wp-config-sample.php. Generating custom wp-config.php configurations...")
            content = sample_path.read_text(encoding="utf-8")
            
            # Formulate database host string
            host_str = params.get("db_host", "127.0.0.1").strip()
            port_str = params.get("db_port", "3306").strip()
            db_host_config = f"{host_str}:{port_str}"

            # Replace database connection credentials
            content = content.replace("database_name_here", params["db_name"])
            content = content.replace("username_here", "root")
            content = content.replace("password_here", "") 
            content = content.replace("localhost", db_host_config) 
            config_path.write_text(content, encoding="utf-8")
            log_callback(f"Successfully configured DB_HOST to '{db_host_config}' and DB_NAME to '{params['db_name']}'")

        progress_callback("WordPress installed successfully!", 100)
        log_callback(">>> One-Click WordPress Installation Completed Successfully!")
