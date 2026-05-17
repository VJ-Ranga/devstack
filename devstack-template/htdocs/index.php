<?php
declare(strict_types=1);

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$stackRoot = realpath(__DIR__ . '/../');
$statusScript = $stackRoot . '/tools/status.ps1';

// Get server software signature
$serverSoftware = $_SERVER['SERVER_SOFTWARE'] ?? 'Web Server';
$isNginx = stripos($serverSoftware, 'nginx') !== false;
$isApache = stripos($serverSoftware, 'apache') !== false;

// Query current service status
$status = ['services' => [], 'generated_at' => date('Y-m-d H:i:s'), 'machine' => php_uname('n')];
if (is_file($statusScript)) {
    $json = shell_exec('powershell -NoProfile -ExecutionPolicy Bypass -File ' . escapeshellarg($statusScript));
    $decoded = is_string($json) ? json_decode($json, true) : null;
    if (is_array($decoded) && isset($decoded['services'])) {
        $status = $decoded;
    }
}

// Build counts
$running = 0;
foreach (($status['services'] ?? []) as $svc) {
    if (($svc['state'] ?? '') === 'running') {
        $running++;
    }
}
$total = count($status['services']);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevStack Local Hub</title>
    <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon">
    <link rel="icon" href="/favicon.png" type="image/png">
    <style>
        :root {
            --bg: #F5F3F0; /* Premium warm ivory paper background */
            --canvas: #FFFFFF; /* Pure white cards */
            --border: #E5E2DC; /* Soft warm sand border */
            --text-main: #1E1B18; /* Deep warm charcoal */
            --text-muted: #5E5B56; /* Soft warm gray */
            --accent: #E55B3C; /* Organic burnt terracotta */
            --accent-hover: #CC4E30;
            --accent-pressed: #B23F23;
            
            /* Status Badges */
            --running-bg: #E6ECE4;
            --running-text: #335E28;
            --running-border: #4B7D3F;
            
            --stopped-bg: #F5E9E6;
            --stopped-text: #9C3A25;
            --stopped-border: #C24F36;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, "SF Pro Text", "SF Pro Display", "Helvetica Neue", "Segoe UI", sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.5;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }

        .container {
            max-width: 780px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        /* Premium Rounded Cards */
        .card {
            background-color: var(--canvas);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.015);
        }

        /* Header Layout */
        .header-card {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        .brand-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent);
            box-shadow: 0 0 10px rgba(229, 91, 60, 0.5);
        }

        h1 {
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }

        .server-badge {
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .server-badge.nginx {
            background-color: #E6ECE4;
            color: #335E28;
            border: 1px solid #4B7D3F;
        }

        .server-badge.apache {
            background-color: #EBF3F5;
            color: #1F5160;
            border: 1px solid #306E80;
        }

        .server-badge.generic {
            background-color: #F0EDEB;
            color: #5E534C;
            border: 1px solid #8C786B;
        }

        /* Subtitle Muted */
        .subtitle {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        /* Quick Links Grid */
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }

        .quick-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
            background-color: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            text-decoration: none;
            color: var(--text-main);
            transition: all 0.2s ease;
        }

        .quick-item:hover {
            background-color: #FAF9F6;
            border-color: var(--accent);
            transform: translateY(-2px);
        }

        .quick-title {
            font-size: 14px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .quick-title span {
            color: var(--accent);
        }

        .quick-desc {
            font-size: 11px;
            color: var(--text-muted);
        }

        /* Services Grid */
        .services-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 16px;
        }

        .service-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background-color: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 4px solid var(--border);
            border-radius: 12px;
        }

        .service-row.running {
            border-left-color: var(--running-border);
        }

        .service-row.stopped {
            border-left-color: var(--stopped-border);
        }

        .service-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .service-name {
            font-size: 13px;
            font-weight: 700;
        }

        .service-meta {
            font-size: 11px;
            color: var(--text-muted);
        }

        .badge {
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 10px;
        }

        .badge.running {
            background-color: var(--running-bg);
            color: var(--running-text);
        }

        .badge.stopped {
            background-color: var(--stopped-bg);
            color: var(--stopped-text);
        }

        /* Section Title styling */
        h2 {
            font-size: 14px;
            font-weight: 800;
            color: var(--text-muted);
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }

        /* Footer & Credit Cards */
        .footer-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 16px;
            border-color: var(--border);
        }

        .footer-logo {
            font-size: 14px;
            font-weight: 800;
            letter-spacing: -0.3px;
        }

        .footer-logo span {
            color: var(--accent);
        }

        .credit-text {
            font-size: 12px;
            color: var(--text-muted);
            max-width: 480px;
        }

        .credit-text a {
            color: var(--accent);
            text-decoration: none;
            font-weight: 700;
        }

        .credit-text a:hover {
            text-decoration: underline;
        }

        /* Designer Buttons */
        .buttons-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            text-decoration: none;
            border-radius: 12px;
            padding: 8px 18px;
            height: 36px;
            transition: all 0.15s ease;
            cursor: pointer;
        }

        .btn-primary {
            background-color: var(--accent);
            color: #FFFFFF;
            border: none;
        }

        .btn-primary:hover {
            background-color: var(--accent-hover);
        }

        .btn-secondary {
            background-color: #FFFFFF;
            color: var(--text-main);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background-color: #FAF9F6;
            border-color: var(--text-muted);
        }

        @media (max-width: 600px) {
            .header-card {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    </style>
</head>
<body>

<div class="container">

    <!-- Brand Header -->
    <div class="card header-card">
        <div class="brand-section">
            <div class="brand-dot"></div>
            <div>
                <h1>DevStack Local Portal</h1>
                <p class="subtitle">Quick navigation and status for your offline local stack.</p>
            </div>
        </div>
        
        <?php if ($isNginx): ?>
            <div class="server-badge nginx">🟢 Served by Nginx</div>
        <?php elseif ($isApache): ?>
            <div class="server-badge apache">🟢 Served by Apache</div>
        <?php else: ?>
            <div class="server-badge generic">🟢 Served by <?php echo htmlspecialchars(explode('/', $serverSoftware)[0]); ?></div>
        <?php endif; ?>
    </div>

    <!-- Quick Access Hub -->
    <div class="card">
        <h2>Quick Access Hub</h2>
        <div class="quick-grid">
            <a href="/phpmyadmin/" target="_blank" class="quick-item">
                <div class="quick-title"><span>📂</span> phpMyAdmin</div>
                <div class="quick-desc">Manage local databases, run queries, and export schemas.</div>
            </a>
            <a href="/dashboard/" class="quick-item">
                <div class="quick-title"><span>📊</span> Control Dashboard</div>
                <div class="quick-desc">Read server logs, control tasks, and inspect settings.</div>
            </a>
            <a href="/phpinfo.php" target="_blank" class="quick-item">
                <div class="quick-title"><span>ℹ️</span> PHP Configuration</div>
                <div class="quick-desc">Check runtime variables, loaded modules, and active limits.</div>
            </a>
        </div>
    </div>

    <!-- Live Service Monitor -->
    <div class="card">
        <h2>Live Service Monitor</h2>
        <p class="subtitle" style="margin-bottom: 4px;">Running <?php echo $running; ?> of <?php echo $total; ?> active local nodes.</p>
        
        <div class="services-list">
            <?php 
            $serviceNames = [
                'apache' => 'Apache HTTP Server',
                'nginx' => 'Nginx Web Server',
                'php' => 'PHP FastCGI Process',
                'mysql' => 'MariaDB Database'
            ];

            foreach (($status['services'] ?? []) as $svc): 
                $key = $svc['key'] ?? '';
                $state = $svc['state'] ?? 'stopped';
                $name = $serviceNames[$key] ?? ucfirst($key);
                $port = $svc['port'] ?? 0;
            ?>
                <div class="service-row <?php echo $state === 'running' ? 'running' : 'stopped'; ?>">
                    <div class="service-info">
                        <div class="service-name"><?php echo htmlspecialchars($name); ?></div>
                        <div class="service-meta">Port <?php echo $port; ?>  •  Local Loopback Node</div>
                    </div>
                    <div class="badge <?php echo $state === 'running' ? 'running' : 'stopped'; ?>">
                        <?php echo $state === 'running' ? 'Active' : 'Offline'; ?>
                    </div>
                </div>
            <?php endforeach; ?>
        </div>
    </div>

    <!-- Creator & Support Credit Banner -->
    <div class="card footer-card">
        <div class="footer-logo">Dev<span>Stack</span></div>
        <p class="credit-text">
            Developed by <a href="https://vjranga.com" target="_blank">VJ-Ranga</a>.
        </p>
        <div class="buttons-row">
            <a href="https://github.com/VJ-Ranga" target="_blank" class="btn btn-secondary">⭐️ GitHub Profile</a>
        </div>
    </div>

</div>

</body>
</html>
