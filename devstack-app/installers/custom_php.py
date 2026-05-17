import os
import shutil
from pathlib import Path

class CustomPHPInstaller:
    meta = {
        "id": "custom_php",
        "name": "Custom PHP App",
        "desc": "Initialize a clean local workspace for custom PHP scripts and web development.",
        "icon": "⚡",
        "category": "Custom Development"
    }

    @staticmethod
    def get_inputs():
        return [
            {"key": "site_name", "label": "Site Folder Name", "type": "text", "default": "my_php_app"},
            {"key": "site_title", "label": "App Title", "type": "text", "default": "My Custom PHP App"},
            {"key": "db_host", "label": "Database Host", "type": "text", "default": "127.0.0.1"},
            {"key": "db_port", "label": "Database Port", "type": "text", "default": "3306"},
            {"key": "db_name", "label": "Database Name", "type": "text", "default": "my_php_app"},
        ]

    @classmethod
    def install(cls, target_dir: Path, params: dict, mysql_conn, progress_callback, log_callback):
        # 1. Create target folder
        progress_callback("Creating local workspace...", 20)
        log_callback(f"Creating local target directory: htdocs/{params['site_name']}")
        os.makedirs(target_dir, exist_ok=True)

        # 2. Setup MariaDB database
        progress_callback("Creating MariaDB database...", 50)
        db_name = params.get("db_name", "").strip()
        if db_name:
            log_callback(f"Initializing database `{db_name}`...")
            cursor = mysql_conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.close()
            log_callback(f"Database `{db_name}` is ready.")

        # 3. Write a gorgeous, premium index.php landing page
        progress_callback("Writing environment details...", 80)
        index_php = target_dir / "index.php"
        
        site_title = params.get("site_title", "My Custom PHP App")
        db_host = params.get("db_host", "127.0.0.1")
        db_port = params.get("db_port", "3306")
        
        content = f"""<?php
$title = "{site_title}";
$db_host = "{db_host}";
$db_port = "{db_port}";
$db_name = "{db_name}";

// Dynamic MariaDB loopback test
$db_status = "Not Connected";
$db_color = "#E55B3C";
try {{
    $conn = new PDO("mysql:host=$db_host;port=$db_port;dbname=$db_name", "root", "");
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $db_status = "Connected Successfully!";
    $db_color = "#2aa198";
}} catch (Exception $e) {{
    $db_status = "Connection Failed: " . $e->getMessage();
}}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $title; ?> | DevStack</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Outfit', sans-serif;
            background: linear-gradient(135deg, #13131a 0%, #1e1e2d 100%);
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            backdrop-filter: blur(10px);
        }}
        .header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
        }}
        .icon {{
            font-size: 36px;
            background: rgba(229, 91, 60, 0.1);
            border: 1px solid rgba(229, 91, 60, 0.2);
            border-radius: 12px;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        h1 {{
            font-weight: 700;
            font-size: 24px;
            background: linear-gradient(90deg, #ffffff 0%, #E55B3C 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            color: #b0b0bc;
            font-size: 14px;
            margin-top: 4px;
        }}
        .section {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }}
        .section-title {{
            font-weight: 600;
            font-size: 12px;
            color: #E55B3C;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }}
        .stat-box {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 8px;
            padding: 12px;
        }}
        .stat-label {{
            font-size: 11px;
            color: #8c8c9c;
            margin-bottom: 4px;
        }}
        .stat-value {{
            font-size: 14px;
            font-weight: 600;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .footer {{
            text-align: center;
            margin-top: 24px;
            font-size: 12px;
            color: #8c8c9c;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="icon">⚡</div>
            <div>
                <h1><?php echo $title; ?></h1>
                <p class="subtitle">Powered by local DevStack development environment</p>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Database Loopback Status</div>
            <div class="stat-value" style="color: <?php echo $db_color; ?>;">
                <span class="badge" style="background-color: <?php echo $db_color; ?>22; color: <?php echo $db_color; ?>; margin-right: 6px;">●</span>
                <?php echo $db_status; ?>
            </div>
        </div>

        <div class="section">
            <div class="section-title">System Environment Info</div>
            <div class="grid">
                <div class="stat-box">
                    <div class="stat-label">PHP Version</div>
                    <div class="stat-value"><?php echo PHP_VERSION; ?></div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Web Server</div>
                    <div class="stat-value"><?php echo $_SERVER['SERVER_SOFTWARE']; ?></div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Database Host</div>
                    <div class="stat-value"><?php echo $db_host . ":" . $db_port; ?></div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Active Database</div>
                    <div class="stat-value"><?php echo $db_name; ?></div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Loaded Vital Extensions</div>
            <div style="font-size: 12px; line-height: 1.6; color: #d0d0dc;">
                <?php
                $exts = ['mysqli', 'pdo_mysql', 'curl', 'openssl', 'gd', 'mbstring'];
                foreach ($exts as $ext) {{
                    $loaded = extension_loaded($ext) ? "✓" : "✗";
                    $color = extension_loaded($ext) ? "#2aa198" : "#E55B3C";
                    echo "<span style='color:$color; font-weight:bold; margin-right:12px;'>$ext ($loaded)</span>";
                }}
                ?>
            </div>
        </div>

        <div class="footer">
            Start writing your code in <strong>htdocs/<?php echo basename(__DIR__); ?>/index.php</strong>!
        </div>
    </div>
</body>
</html>
"""
        index_php.write_text(content, encoding="utf-8")
        log_callback("index.php landing page written successfully.")
        
        progress_callback("Custom PHP app installed!", 100)
        log_callback(">>> Custom PHP environment initialized successfully!")
