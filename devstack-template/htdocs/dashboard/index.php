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
        $notice = 'Start command sent.';
    } elseif ($action === 'stop') {
        runCmd('powershell -NoProfile -ExecutionPolicy Bypass -File "' . $stackRoot . '\\tools\\control.ps1" stop all');
        $notice = 'Stop command sent.';
    } elseif ($action === 'restart') {
        runCmd('powershell -NoProfile -ExecutionPolicy Bypass -File "' . $stackRoot . '\\tools\\control.ps1" restart all');
        $notice = 'Restart command sent.';
    } elseif (in_array($action, ['svc_start', 'svc_stop', 'svc_restart'], true)) {
        $svc = preg_replace('/[^a-z]/', '', (string)($_POST['service'] ?? ''));
        if ($svc !== '') {
            $verb = str_replace('svc_', '', $action);
            runCmd('powershell -NoProfile -ExecutionPolicy Bypass -File "' . $stackRoot . '\\tools\\control.ps1" ' . $verb . ' ' . $svc);
            $notice = strtoupper($svc) . ' ' . $verb . ' command sent.';
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
    ['label' => 'Open Nginx', 'href' => $frontendBase . '/'],
    ['label' => 'Open Apache', 'href' => $apacheBase . '/'],
    ['label' => 'Open phpMyAdmin', 'href' => $frontendBase . '/phpmyadmin/'],
    ['label' => 'Open Dashboard', 'href' => $frontendBase . '/dashboard/'],
];

$serviceMeta = [
    'apache' => ['role' => 'Backend web server', 'open' => $apacheBase . '/'],
    'nginx' => ['role' => 'Main web entry point', 'open' => $frontendBase . '/'],
    'php' => ['role' => 'PHP runtime', 'open' => null],
    'mysql' => ['role' => 'Database server', 'open' => $frontendBase . '/phpmyadmin/'],
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
        'Apache Error' => lastLines(readTail($stackRoot . '/apache/logs/error_log'), 20),
        'Nginx Error' => lastLines(readTail($stackRoot . '/nginx/logs/error.log'), 20),
        'MariaDB Error' => $mysqlLogPath !== '' ? lastLines(readTail($mysqlLogPath), 20) : 'No MariaDB .err log file yet.',
    ];
}
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>DevStack Dashboard</title>
    <style>
        :root { --bg:#f3f3f3; --panel:#ffffff; --line:#e1e1e1; --text:#1f1f1f; --muted:#5f5f5f; --accent:#0f6cbd; --accent-hover:#115ea3; --hover:#f8f8f8; --success:#107c10; --success-soft:#f2fbf4; --warning:#986f0b; --warning-soft:#fff8ee; --danger:#d13438; --danger-soft:#fff4f4; }
        * { box-sizing:border-box; }
        body { margin:0; font-family:"Segoe UI",sans-serif; background:var(--bg); color:var(--text); }
        .wrap { max-width:1100px; margin:24px auto; padding:0 16px 24px; }
        .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:18px; margin-bottom:16px; }
        h1 { margin:0; font-size:24px; }
        h2 { margin:0 0 10px; font-size:15px; }
        p { margin:0; }
        .muted { color:var(--muted); font-size:13px; line-height:1.5; }
        .stack { display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; align-items:flex-start; }
        .actions, .row { display:flex; flex-wrap:wrap; gap:10px; }
        .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }
        .service-list { display:flex; flex-direction:column; gap:0; }
        .service-row { display:flex; justify-content:space-between; gap:12px; align-items:center; border:1px solid var(--line); border-radius:8px; padding:14px 16px; background:var(--panel); }
        .service-row + .service-row { margin-top:10px; }
        .btn { display:inline-flex; align-items:center; justify-content:center; min-height:38px; padding:0 16px; border-radius:8px; border:1px solid transparent; font-weight:600; font-size:13px; text-decoration:none; cursor:pointer; }
        .btn-primary { background:var(--accent); color:#fff; }
        .btn-primary:hover { background:var(--accent-hover); border-color:var(--accent-hover); }
        .btn-danger { background:#dc2626; color:#fff; }
        .btn-danger:hover { background:#b91c1c; }
        .btn-outline { background:#fff; color:var(--text); border-color:var(--line); }
        .btn-outline:hover { background:var(--hover); }
        .chip { display:inline-flex; align-items:center; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700; border:1px solid currentColor; }
        .ok { background:var(--success-soft); color:var(--success); }
        .warn { background:var(--warning-soft); color:var(--warning); }
        .bad { background:var(--danger-soft); color:var(--danger); }
        .service-meta { display:flex; flex-wrap:wrap; gap:8px; margin-top:6px; }
        .tag { background:#fbfbfb; color:var(--muted); border:1px solid var(--line); border-radius:999px; padding:3px 10px; font-size:11px; font-weight:600; }
        pre { background:#ffffff; color:var(--text); padding:12px; border:1px solid var(--line); border-radius:8px; overflow:auto; max-height:220px; white-space:pre-wrap; }
        @media (max-width:760px) { .stack { flex-direction:column; } }
    </style>
</head>
<body>
<div class="wrap">
    <div class="panel">
        <div class="stack">
            <div>
                <h1>DevStack Dashboard</h1>
                <p class="muted">Start, stop, and open the tools you need from one clean control surface.</p>
                <div class="row" style="margin-top:10px;">
                    <span class="chip <?= $running === $total && $total > 0 ? 'ok' : ($running > 0 || $partial > 0 ? 'warn' : 'bad') ?>">
                        <?= $running === $total && $total > 0 ? 'All Running' : ($running > 0 || $partial > 0 ? 'Needs Attention' : 'Stopped') ?>
                    </span>
                    <span class="muted">Updated: <?= htmlspecialchars((string)$status['generated_at']) ?></span>
                </div>
            </div>
            <form method="post" class="actions">
                <button class="btn btn-primary" name="action" value="start">Start All</button>
                <button class="btn btn-danger" name="action" value="stop">Stop All</button>
                <button class="btn btn-outline" name="action" value="restart">Restart All</button>
            </form>
        </div>
        <?php if ($notice !== ''): ?>
            <p style="margin-top:12px;font-weight:600;"><?= htmlspecialchars($notice) ?></p>
        <?php endif; ?>
    </div>

    <div class="panel">
        <h2>Quick Access</h2>
        <div class="grid">
            <?php foreach ($quickLinks as $link): ?>
                <a class="btn btn-outline" href="<?= htmlspecialchars($link['href']) ?>" target="_blank"><?= htmlspecialchars($link['label']) ?></a>
            <?php endforeach; ?>
        </div>
    </div>

    <div class="panel">
        <h2>Services</h2>
        <p class="muted" style="margin-bottom:14px;">Running <?= $running ?> of <?= $total ?> services. Partial: <?= $partial ?>. Stopped: <?= max(0, $total - $running - $partial) ?>.</p>
        <div class="service-list">
            <?php foreach (($status['services'] ?? []) as $svc):
                $key = (string)($svc['key'] ?? '');
                $state = (string)($svc['state'] ?? 'stopped');
                $meta = $serviceMeta[$key] ?? ['role' => 'Service', 'open' => null];
                $chipClass = $state === 'running' ? 'ok' : ($state === 'partial' ? 'warn' : 'bad');
                $label = $state === 'partial' ? 'Needs Attention' : ucfirst($state);
            ?>
            <div class="service-row">
                <div style="flex:1;min-width:220px;">
                    <div>
                        <strong><?= htmlspecialchars((string)$svc['name']) ?></strong>
                        <p class="muted" style="margin-top:4px;"><?= htmlspecialchars((string)$meta['role']) ?></p>
                    </div>
                    <div class="service-meta">
                        <span class="tag">Process <?= htmlspecialchars((string)$svc['process']) ?>.exe</span>
                        <span class="tag">Port <?= htmlspecialchars((string)$svc['port']) ?></span>
                    </div>
                </div>
                <span class="chip <?= $chipClass ?>"><?= htmlspecialchars($label) ?></span>
                <form method="post" class="actions">
                    <input type="hidden" name="service" value="<?= htmlspecialchars($key) ?>">
                    <button class="btn btn-primary" name="action" value="svc_start">Start</button>
                    <button class="btn btn-danger" name="action" value="svc_stop">Stop</button>
                    <button class="btn btn-outline" name="action" value="svc_restart">Restart</button>
                    <?php if (!empty($meta['open'])): ?>
                        <a class="btn btn-outline" href="<?= htmlspecialchars((string)$meta['open']) ?>" target="_blank">Open</a>
                    <?php endif; ?>
                </form>
            </div>
            <?php endforeach; ?>
        </div>
    </div>

    <div class="panel">
        <div class="stack">
            <div>
                <h2>Logs</h2>
                <p class="muted">Logs stay out of the way until you need them.</p>
            </div>
            <div class="actions">
                <?php if ($showLogs): ?>
                    <a class="btn btn-outline" href="/dashboard/">Hide Logs</a>
                <?php else: ?>
                    <a class="btn btn-outline" href="/dashboard/?logs=1">Show Logs</a>
                <?php endif; ?>
            </div>
        </div>
        <?php if ($showLogs): ?>
            <div class="grid" style="margin-top:14px;">
                <?php foreach ($logs as $title => $content): ?>
                    <div>
                        <p class="muted" style="margin-bottom:8px;"><?= htmlspecialchars($title) ?></p>
                        <pre><?= htmlspecialchars($content) ?></pre>
                    </div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>
    </div>
</div>
</body>
</html>
