<?php
/**
 * DevStack Local Portal — http://localhost/
 * Shows all local sites, live service status, quick links.
 * Read-only — use DevStack Manager desktop app for start/stop control.
 */
declare(strict_types=1);
header('Content-Type: text/html; charset=UTF-8');
header('Cache-Control: no-store');

// Scan htdocs for local site folders
$excluded = ['dashboard', 'phpmyadmin', 'assets'];
$sites = [];
foreach (scandir(__DIR__) ?: [] as $entry) {
    if (in_array($entry, $excluded, true) || str_starts_with($entry, '.')) continue;
    if (!is_dir(__DIR__ . '/' . $entry)) continue;
    $p = __DIR__ . '/' . $entry;
    if (file_exists("$p/wp-config.php") || is_dir("$p/wp-includes")) {
        $type = 'WordPress'; $url = "/$entry/"; $color = '#21759b';
    } elseif (file_exists("$p/artisan")) {
        $type = 'Laravel'; $url = "/$entry/public/"; $color = '#FF2D20';
    } elseif (file_exists("$p/core/lib/Drupal.php")) {
        $type = 'Drupal'; $url = "/$entry/"; $color = '#0678BE';
    } else {
        $type = 'PHP'; $url = "/$entry/"; $color = '#7B4F9E';
    }
    $sites[] = compact('entry', 'type', 'url', 'color');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DevStack Local Portal</title>
<link rel="icon" href="/dashboard/favicon.ico">
<style>
:root{--bg:#F5F3F0;--canvas:#fff;--border:#E5E2DC;--text:#1E1B18;--muted:#5E5B56;--accent:#E55B3C}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding:36px 20px}
.wrap{max-width:860px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
.hdr{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.brand{display:flex;align-items:center;gap:10px}
.dot{width:9px;height:9px;border-radius:50%;background:var(--accent);box-shadow:0 0 8px rgba(229,91,60,.5)}
h1{font-size:20px;font-weight:800;letter-spacing:-.4px}
.tagline{font-size:12px;color:var(--muted);margin-top:2px}
.card{background:var(--canvas);border:1px solid var(--border);border-radius:14px;padding:20px 22px}
h2{font-size:11px;font-weight:800;color:var(--muted);letter-spacing:.8px;text-transform:uppercase;margin-bottom:14px}
.pills{display:flex;flex-wrap:wrap;gap:8px}
.pill{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:99px;font-size:12px;font-weight:600;border:1px solid var(--border);background:#fff}
.pill .led{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.led.running{background:#4B7D3F}.led.stopped{background:#C24F36}.led.partial{background:#EAB05E}.led.unknown{background:#bbb}
.qgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.qlink{display:flex;align-items:center;justify-content:center;text-align:center;background:#FAF9F6;border:1px solid var(--border);border-radius:10px;padding:12px 10px;text-decoration:none;font-size:12px;font-weight:700;color:var(--text);transition:all .15s}
.qlink:hover{border-color:var(--accent);background:#fff;transform:translateY(-1px)}
.sgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.scard{display:flex;flex-direction:column;gap:8px;background:var(--canvas);border:1px solid var(--border);border-left:3px solid #ccc;border-radius:12px;padding:15px;text-decoration:none;color:var(--text);transition:all .15s}
.scard:hover{box-shadow:0 2px 10px rgba(0,0,0,.07);transform:translateY(-1px)}
.scard .badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;color:#fff;display:inline-block;width:fit-content}
.scard .name{font-size:14px;font-weight:700}
.scard .path{font-size:11px;color:var(--muted)}
.empty{text-align:center;padding:32px;color:var(--muted);font-size:13px;line-height:1.7}
.foot{text-align:center;font-size:11px;color:var(--muted)}
.foot a{color:var(--accent);text-decoration:none;font-weight:600}
</style>
</head>
<body>
<div class="wrap">

  <div class="hdr">
    <div class="brand">
      <div class="dot"></div>
      <div>
        <h1>DevStack Local Portal</h1>
        <p class="tagline">Your local development environment</p>
      </div>
    </div>
    <div id="overall" style="font-size:12px;font-weight:700;color:var(--muted)">Checking…</div>
  </div>

  <div class="card">
    <h2>Live Service Monitor</h2>
    <div class="pills" id="pills">
      <div class="pill"><span class="led unknown"></span>Loading…</div>
    </div>
  </div>

  <div class="card">
    <h2>Quick Access Hub</h2>
    <div class="qgrid">
      <a class="qlink" href="/dashboard/">📊 Status Dashboard</a>
      <a class="qlink" href="/phpmyadmin/">🗄️ phpMyAdmin</a>
      <a class="qlink" href="/phpinfo.php">ℹ️ PHP Info</a>
    </div>
  </div>

  <div class="card">
    <h2>Your Local Sites</h2>
    <?php if (empty($sites)): ?>
      <div class="empty">
        No sites yet.<br>
        Open <strong>DevStack Manager → Websites → Install Website</strong> to get started.
      </div>
    <?php else: ?>
      <div class="sgrid">
        <?php foreach ($sites as $s): ?>
          <a class="scard" href="<?= htmlspecialchars($s['url']) ?>"
             style="border-left-color:<?= htmlspecialchars($s['color']) ?>">
            <span class="badge" style="background:<?= htmlspecialchars($s['color']) ?>">
              <?= htmlspecialchars($s['type']) ?>
            </span>
            <div class="name"><?= htmlspecialchars($s['entry']) ?></div>
            <div class="path">localhost<?= htmlspecialchars($s['url']) ?></div>
          </a>
        <?php endforeach; ?>
      </div>
    <?php endif; ?>
  </div>

  <div class="foot">
    DevStack by <a href="https://vjranga.com" target="_blank">VJ-Ranga</a>
    &nbsp;·&nbsp;
    <a href="/dashboard/">Control Panel</a>
  </div>

</div>
<script>
async function refresh() {
  try {
    const d = await fetch('/dashboard/api.php', { cache:'no-store' }).then(r => r.json());
    const s = d.services || [], run = s.filter(x => x.state === 'running').length;
    const all = run === s.length && s.length;
    document.getElementById('overall').textContent = `${all ? '●' : '◐'} ${run}/${s.length} Running`;
    document.getElementById('overall').style.color = all ? '#335E28' : run ? '#8F621D' : '#9C3A25';
    document.getElementById('pills').innerHTML = s.map(x =>
      `<div class="pill"><span class="led ${x.state}"></span>${x.name} <span style="color:#bbb;font-size:10px">:${x.port}</span></div>`
    ).join('');
  } catch { document.getElementById('overall').textContent = 'Stack offline'; }
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
