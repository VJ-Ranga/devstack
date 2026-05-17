<?php
declare(strict_types=1);

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$stackRoot = realpath(__DIR__ . '/../../');
$statusScript = $stackRoot . '/tools/status.ps1';
$apacheConf = $stackRoot . '/apache/conf/httpd.conf';

function runCmd(string $command): string {
    $out = shell_exec('cmd /c ' . escapeshellarg($command) . ' 2>&1');
    return is_string($out) ? trim($out) : '';
}

function readTail(string $path, int $maxBytes = 7000): string {
    if (!is_file($path)) {
        return 'File not found: ' . $path;
    }
    $size = filesize($path);
    if ($size === false || $size <= 0) {
        return '(empty)';
    }
    $fp = fopen($path, 'rb');
    if ($fp === false) {
        return '(cannot read file)';
    }
    $start = max(0, $size - $maxBytes);
    fseek($fp, $start);
    $content = stream_get_contents($fp);
    fclose($fp);
    return trim((string)$content);
}

function lastLines(string $text, int $count = 20): string {
    $lines = preg_split('/\r\n|\r|\n/', $text) ?: [];
    return trim(implode(PHP_EOL, array_slice($lines, -$count)));
}

$notice = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    $action = (string)$_POST['action'];
    if ($action === 'start') {
        runCmd('powershell -NoProfile -ExecutionPolicy Bypass -File "' . $stackRoot . '\\tools\\control.ps1" start all');
        $notice = 'All services started successfully.';
    } elseif ($action === 'stop') {
        runCmd('powershell -NoProfile -ExecutionPolicy Bypass -File "' . $stackRoot . '\\tools\\control.ps1" stop all');
        $notice = 'All services stopped successfully.';
    } elseif ($action === 'restart') {
        runCmd('powershell -NoProfile -ExecutionPolicy Bypass -File "' . $stackRoot . '\\tools\\control.ps1" restart all');
        $notice = 'All services restarted successfully.';
    } elseif (in_array($action, ['svc_start', 'svc_stop', 'svc_restart'], true)) {
        $svc = preg_replace('/[^a-z]/', '', (string)($_POST['service'] ?? ''));
        if ($svc !== '') {
            $verb = str_replace('svc_', '', $action);
            runCmd('powershell -NoProfile -ExecutionPolicy Bypass -File "' . $stackRoot . '\\tools\\control.ps1" ' . $verb . ' ' . $svc);
            $notice = strtoupper($svc) . ' ' . $verb . ' command sent successfully.';
        }
    }
}

$status = ['services' => [], 'generated_at' => date('Y-m-d H:i:s'), 'machine' => php_uname('n')];
if (is_file($statusScript)) {
    $json = shell_exec('powershell -NoProfile -ExecutionPolicy Bypass -File ' . escapeshellarg($statusScript));
    $decoded = is_string($json) ? json_decode($json, true) : null;
    if (is_array($decoded) && isset($decoded['services'])) {
        $status = $decoded;
    }
}

$httpdConf = is_file($apacheConf) ? (file_get_contents($apacheConf) ?: '') : '';
preg_match('/^\s*Listen\s+(\d+)\s*$/mi', $httpdConf, $m1);
$apachePort = $m1[1] ?? '8088';

$host = $_SERVER['HTTP_HOST'] ?? 'localhost';
$scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
$frontendBase = $scheme . '://' . $host;
$apacheBase = 'http://localhost:' . $apachePort;

$quickLinks = [
    ['label' => '📂 phpMyAdmin', 'href' => $frontendBase . '/phpmyadmin/'],
    ['label' => '🌐 Landing Page', 'href' => $frontendBase . '/'],
    ['label' => '💻 Apache Root', 'href' => $apacheBase . '/'],
    ['label' => 'ℹ️ PHP Info', 'href' => $frontendBase . '/phpinfo.php']
];

$serviceMeta = [
    'apache' => ['role' => 'Backend web server', 'open' => $apacheBase . '/'],
    'nginx' => ['role' => 'Main web entry point', 'open' => $frontendBase . '/'],
    'php' => ['role' => 'PHP FastCGI process', 'open' => null],
    'mysql' => ['role' => 'MariaDB database node', 'open' => $frontendBase . '/phpmyadmin/'],
];

$running = 0;
$partial = 0;
foreach (($status['services'] ?? []) as $svc) {
    if (($svc['state'] ?? '') === 'running') {
        $running++;
    } elseif (($svc['state'] ?? '') === 'partial') {
        $partial++;
    }
}
$total = count($status['services']);

$showLogs = isset($_GET['logs']) && $_GET['logs'] === '1';
$logs = [];
if ($showLogs) {
    $mysqlLogPath = '';
    $candidates = glob($stackRoot . '/mysql/data/*.err') ?: [];
    if (count($candidates) > 0) {
        rsort($candidates);
        $mysqlLogPath = $candidates[0];
    }
    $logs = [
        'Apache Error logs' => lastLines(readTail($stackRoot . '/apache/logs/error_log'), 20),
        'Nginx Error logs' => lastLines(readTail($stackRoot . '/nginx/logs/error.log'), 20),
        'MariaDB System logs' => $mysqlLogPath !== '' ? lastLines(readTail($mysqlLogPath), 20) : 'No MariaDB .err log file yet.',
    ];
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevStack Control Dashboard</title>
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

            --partial-bg: #F5EDE2;
            --partial-text: #8F621D;
            --partial-border: #EAB05E;
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

        .server-badge.status-ok {
            background-color: var(--running-bg);
            color: var(--running-text);
            border: 1px solid var(--running-border);
        }

        .server-badge.status-attention {
            background-color: var(--partial-bg);
            color: var(--partial-text);
            border: 1px solid var(--partial-border);
        }

        .server-badge.status-bad {
            background-color: var(--stopped-bg);
            color: var(--stopped-text);
            border: 1px solid var(--stopped-border);
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
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 10px;
            margin-top: 16px;
        }

        .quick-item {
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px;
            text-decoration: none;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-main);
            transition: all 0.2s ease;
        }

        .quick-item:hover {
            background-color: #FAF9F6;
            border-color: var(--accent);
            transform: translateY(-2px);
        }

        /* Services Grid */
        .services-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 16px;
        }

        .service-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            padding: 16px;
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

        .service-row.partial {
            border-left-color: var(--partial-border);
        }

        .service-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
            flex: 1;
            min-width: 220px;
        }

        .service-name {
            font-size: 13px;
            font-weight: 700;
        }

        .service-meta-tags {
            display: flex;
            gap: 6px;
            margin-top: 4px;
        }

        .meta-tag {
            background-color: #FAF9F6;
            color: var(--text-muted);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 600;
        }

        .badge {
            font-size: 10px;
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

        .badge.partial {
            background-color: var(--partial-bg);
            color: var(--partial-text);
        }

        /* Section Title styling */
        h2 {
            font-size: 14px;
            font-weight: 800;
            color: var(--text-muted);
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }

        /* Action Buttons */
        .actions-form {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            text-decoration: none;
            border-radius: 10px;
            padding: 0 12px;
            height: 30px;
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

        .btn-danger {
            background-color: var(--stopped-bg);
            color: var(--stopped-text);
            border: 1px solid var(--stopped-border);
        }

        .btn-danger:hover {
            background-color: #ECDCD8;
        }

        /* Logs Output */
        .logs-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 16px;
            margin-top: 16px;
        }

        .log-panel {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .log-title {
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
        }

        pre {
            background-color: #FAF9F6;
            color: var(--text-main);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
            font-family: "SF Mono", Consolas, Monaco, "Andale Mono", monospace;
            font-size: 11px;
            overflow-x: auto;
            white-space: pre-wrap;
            max-height: 200px;
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

        .btn-large {
            height: 36px;
            padding: 0 18px;
            border-radius: 12px;
            font-size: 12px;
        }

        .notice-banner {
            background-color: var(--running-bg);
            color: var(--running-text);
            border: 1px solid var(--running-border);
            border-radius: 12px;
            padding: 10px 16px;
            font-size: 12px;
            font-weight: 700;
            margin-top: 14px;
        }

        @media (max-width: 600px) {
            .header-card {
                flex-direction: column;
                align-items: flex-start;
            }
            .service-row {
                flex-direction: column;
                align-items: flex-start;
            }
            .actions-form {
                width: 100%;
                justify-content: flex-start;
            }
        }
    </style>
</head>
<body>

<div class="container">

    <!-- Control Header -->
    <div class="card header-card">
        <div class="brand-section">
            <div class="brand-dot"></div>
            <div>
                <h1>DevStack Control Center</h1>
                <p class="subtitle">Complete process supervisor and control surface.</p>
            </div>
        </div>
        
        <?php 
        $statusClass = $running === $total && $total > 0 ? 'status-ok' : ($running > 0 || $partial > 0 ? 'status-attention' : 'status-bad');
        $statusLabel = $running === $total && $total > 0 ? 'All Active' : ($running > 0 || $partial > 0 ? 'Needs Attention' : 'Stopped');
        ?>
        <div class="server-badge <?php echo $statusClass; ?>">
            🟢 <?php echo $statusLabel; ?>
        </div>
    </div>

    <!-- Global Operations Card -->
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
            <div>
                <h2>Global Stack Operations</h2>
                <p class="subtitle">Control all running loopback nodes simultaneously.</p>
            </div>
            <form method="post" class="actions-form">
                <button class="btn btn-primary btn-large" name="action" value="start">▶ Start All</button>
                <button class="btn btn-danger btn-large" name="action" value="stop">⏹ Stop All</button>
                <button class="btn btn-secondary btn-large" name="action" value="restart">🔄 Restart All</button>
            </form>
        </div>
        
        <?php if ($notice !== ''): ?>
            <div class="notice-banner">
                💡 <?php echo htmlspecialchars($notice); ?>
            </div>
        <?php endif; ?>
    </div>

    <!-- Quick Access Hub -->
    <div class="card">
        <h2>Quick Access Hub</h2>
        <div class="quick-grid">
            <?php foreach ($quickLinks as $link): ?>
                <a class="quick-item" href="<?php echo htmlspecialchars($link['href']); ?>" target="_blank">
                    <?php echo htmlspecialchars($link['label']); ?>
                </a>
            <?php endforeach; ?>
        </div>
    </div>

    <!-- Live Nodes & Processes -->
    <div class="card">
        <h2>Active Nodes & Processes</h2>
        <p class="subtitle" style="margin-bottom: 4px;">Supervising <?php echo $running; ?> running subprocess nodes.</p>
        
        <div class="services-list">
            <?php 
            foreach (($status['services'] ?? []) as $svc):
                $key = (string)($svc['key'] ?? '');
                $state = (string)($svc['state'] ?? 'stopped');
                $meta = $serviceMeta[$key] ?? ['role' => 'Service', 'open' => null];
                $rowClass = $state === 'running' ? 'running' : ($state === 'partial' ? 'partial' : 'stopped');
            ?>
                <div class="service-row <?php echo $rowClass; ?>">
                    <div class="service-info">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div class="service-name"><?php echo htmlspecialchars((string)$svc['name']); ?></div>
                            <div class="badge <?php echo $rowClass; ?>">
                                <?php echo $state === 'running' ? 'Active' : ($state === 'partial' ? 'Attention' : 'Offline'); ?>
                            </div>
                        </div>
                        <div class="subtitle" style="margin-top: 2px; font-size: 11px;"><?php echo htmlspecialchars((string)$meta['role']); ?></div>
                        <div class="service-meta-tags">
                            <span class="meta-tag">Port <?php echo htmlspecialchars((string)$svc['port']); ?></span>
                            <span class="meta-tag">PID <?php echo htmlspecialchars((string)$svc['process']); ?></span>
                        </div>
                    </div>
                    
                    <form method="post" class="actions-form">
                        <input type="hidden" name="service" value="<?php echo htmlspecialchars($key); ?>">
                        
                        <?php if ($state !== 'running'): ?>
                            <button class="btn btn-primary" name="action" value="svc_start">▶ Start</button>
                        <?php else: ?>
                            <button class="btn btn-danger" name="action" value="svc_stop">⏹ Stop</button>
                        <?php endif; ?>
                        
                        <button class="btn btn-secondary" name="action" value="svc_restart">🔄 Restart</button>
                        
                        <?php if (!empty($meta['open'])): ?>
                            <a class="btn btn-secondary" href="<?php echo htmlspecialchars((string)$meta['open']); ?>" target="_blank">🌐 Open</a>
                        <?php endif; ?>
                    </form>
                </div>
            <?php endforeach; ?>
        </div>
    </div>

    <!-- Real-time Supervisor Logs -->
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2>Real-time Logs</h2>
                <p class="subtitle">Inspect output streams for active instances.</p>
            </div>
            <?php if ($showLogs): ?>
                <a class="btn btn-secondary" href="/dashboard/">🙈 Hide Logs</a>
            <?php else: ?>
                <a class="btn btn-secondary" href="/dashboard/?logs=1">👁 Show Logs</a>
            <?php endif; ?>
        </div>

        <?php if ($showLogs): ?>
            <div class="logs-grid">
                <?php foreach ($logs as $title => $content): ?>
                    <div class="log-panel">
                        <div class="log-title">📂 <?php echo htmlspecialchars($title); ?></div>
                        <pre><?php echo htmlspecialchars($content); ?></pre>
                    </div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>
    </div>

    <!-- Creator & Support Credit Banner -->
    <div class="card footer-card">
        <div class="footer-logo">Dev<span>Stack</span></div>
        <p class="credit-text">
            Developed by <a href="https://vjranga.com" target="_blank">VJ-Ranga</a>.
        </p>
        <div class="buttons-row">
            <a href="https://github.com/VJ-Ranga" target="_blank" class="btn btn-secondary btn-large">⭐️ GitHub Profile</a>
        </div>
    </div>

</div>

</body>
</html>
