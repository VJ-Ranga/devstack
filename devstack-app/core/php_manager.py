import os
import shutil
import urllib.request
import zipfile
from pathlib import Path
from PySide6.QtCore import QThread, Signal

STABLE_PHP_VERSIONS = [
    {"version": "PHP 8.3.7 (x64 Thread Safe)", "folder": "php83", "url": "https://windows.php.net/downloads/releases/archives/php-8.3.7-Win32-vs16-x64.zip"},
    {"version": "PHP 8.2.19 (x64 Thread Safe)", "folder": "php82", "url": "https://windows.php.net/downloads/releases/archives/php-8.2.19-Win32-vs16-x64.zip"},
    {"version": "PHP 8.1.28 (x64 Thread Safe)", "folder": "php81", "url": "https://windows.php.net/downloads/releases/archives/php-8.1.28-Win32-vs16-x64.zip"},
    {"version": "PHP 8.0.30 (x64 Thread Safe)", "folder": "php80", "url": "https://windows.php.net/downloads/releases/archives/php-8.0.30-Win32-vs16-x64.zip"},
    {"version": "PHP 7.4.33 (x64 Thread Safe)", "folder": "php74", "url": "https://windows.php.net/downloads/releases/archives/php-7.4.33-Win32-vc15-x64.zip"},
]


class PHPDownloadWorker(QThread):
    progress = Signal(str, int)  # (Status Message, Percentage)
    finished = Signal(bool, str) # (Success, Message)

    def __init__(self, stack_root: str, version_data: dict):
        super().__init__()
        self.stack_root = Path(stack_root)
        self.version_data = version_data

    def run(self):
        try:
            folder_name = self.version_data["folder"]
            download_url = self.version_data["url"]
            target_folder = self.stack_root / folder_name
            zip_path = self.stack_root / f"{folder_name}.zip"

            if target_folder.exists():
                self.finished.emit(False, f"PHP version is already installed at {target_folder.name}")
                return

            self.progress.emit(f"Downloading {self.version_data['version']}...", 15)
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(download_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                block_size = 1024 * 64
                
                with open(zip_path, 'wb') as f:
                    while True:
                        block = response.read(block_size)
                        if not block:
                            break
                        f.write(block)
                        downloaded += len(block)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 60) + 15
                            self.progress.emit(f"Downloading... {downloaded // 1024} KB / {total_size // 1024} KB", pct)

            self.progress.emit("Extracting PHP package...", 80)
            os.makedirs(target_folder, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_folder)

            if zip_path.exists():
                os.remove(zip_path)

            # Generate/Configure php.ini with vital extensions enabled
            self.progress.emit("Configuring php.ini settings...", 90)
            sample_ini = target_folder / "php.ini-development"
            if not sample_ini.exists():
                sample_ini = target_folder / "php.ini-production"
                
            if sample_ini.exists():
                ini_content = sample_ini.read_text(encoding="utf-8")
                
                replacements = [
                    (";extension_dir = \"ext\"", "extension_dir = \"ext\""),
                    (";extension=curl", "extension=curl"),
                    (";extension=gd", "extension=gd"),
                    (";extension=mbstring", "extension=mbstring"),
                    (";extension=mysqli", "extension=mysqli"),
                    (";extension=openssl", "extension=openssl"),
                    (";extension=pdo_mysql", "extension=pdo_mysql"),
                ]
                for old, new in replacements:
                    ini_content = ini_content.replace(old, new)
                
                ini_content = ini_content.replace(";date.timezone =", "date.timezone = UTC")
                
                (target_folder / "php.ini").write_text(ini_content, encoding="utf-8")

            self.progress.emit("PHP installed successfully!", 100)
            self.finished.emit(True, f"Successfully downloaded, extracted, and configured {self.version_data['version']} as folder '{folder_name}'!")

        except Exception as e:
            self.finished.emit(False, f"Installation failed: {str(e)}")
