<?php
// DevStack Status Dashboard — read-only.
// Use DevStack Manager desktop app to start / stop services.
declare(strict_types=1);
header('Content-Type: text/html; charset=UTF-8');
header('Cache-Control: no-store');

$front = ((!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http')
       . '://' . ($_SERVER['HTTP_HOST'] ?? 'localhost');
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DevStack Dashboard</title>
<link rel="icon" href="/dashboard/favicon.ico">
<link rel="stylesheet" href="/dashboard/style.css">
</head>
<body>
<div class="container">

  <div class="card header-card">
    <div class="brand-section">
      <div class="brand-dot"></div>
      <div>
        <h1>DevStack Dashboard</h1>
        <p class="subtitle">Status monitor · Auto-refreshes every 5 s · <a href="/" style="color:inherit">← Portal</a></p>
      </div>
    </div>
    <span class="server-badge bad" id="overall-badge">Checking…</span>
  </div>

  <!-- Stat strip -->
  <div class="stat-grid">
    <div class="stat"><div class="stat-val" id="stat-services">–</div><div class="stat-lbl">Services Up</div></div>
    <div class="stat"><div class="stat-val" id="stat-php">–</div><div class="stat-lbl">PHP Version</div></div>
    <div class="stat"><div class="stat-val" id="stat-sites">–</div><div class="stat-lbl">Local Sites</div></div>
    <div class="stat"><div class="stat-val" id="stat-time">–</div><div class="stat-lbl">Last Check</div></div>
  </div>

  <div class="card">
    <h2>Quick Access</h2>
    <div class="quick-grid">
      <a class="quick-item" href="<?= $front ?>/"            target="_blank">🌐 Local Portal</a>
      <a class="quick-item" href="<?= $front ?>/phpmyadmin/" target="_blank">🗄️ phpMyAdmin</a>
      <a class="quick-item" href="<?= $front ?>/phpinfo.php" target="_blank">ℹ️ PHP Info</a>
    </div>
  </div>

  <div class="card">
    <h2>Services <span id="svc-summary" style="font-weight:400;font-size:11px;color:#999;margin-left:6px"></span></h2>
    <div class="services-list" id="svc-list"></div>
  </div>

  <div class="card footer-card">
    <div class="footer-logo">Dev<span>Stack</span></div>
    <p class="credit-text">
      To start/stop services use <strong>DevStack Manager</strong> desktop app.<br>
      Developed by <a href="https://vjranga.com" target="_blank">VJ-Ranga</a>
    </p>
  </div>

</div>
<script>
const FRONT = <?= json_encode($front) ?>;

const open = { nginx: FRONT + '/', mysql: FRONT + '/phpmyadmin/' };

async function refresh() {
  try {
    const d = await fetch('/dashboard/api.php', { cache: 'no-store' }).then(r => r.json());
    const s = d.services || [];
    const run = s.filter(x => x.state === 'running').length;
    const ob  = document.getElementById('overall-badge');
    ob.className  = 'server-badge ' + (run === s.length && s.length ? 'ok' : run ? 'warn' : 'bad');
    ob.textContent = run === s.length && s.length ? '● All Active' : run ? '● Partial' : '● Stopped';
    document.getElementById('svc-summary').textContent = `${run}/${s.length} running`;

    // Stat strip
    document.getElementById('stat-services').textContent = `${run}/${s.length}`;
    document.getElementById('stat-php').textContent      = d.php_version || '–';
    document.getElementById('stat-sites').textContent    = (d.site_count ?? '–');
    document.getElementById('stat-time').textContent     = (d.generated_at || '').split(' ')[1] || '–';
    document.getElementById('svc-list').innerHTML = s.map(x => {
      const state = x.state || 'stopped';
      const label = state === 'running' ? 'Active' : state === 'partial' ? 'Attention' : 'Offline';
      const btn   = open[x.key] ? `<a class="btn btn-secondary" href="${open[x.key]}" target="_blank">Open</a>` : '';
      return `<div class="service-row ${state}">
        <div class="service-info">
          <div style="display:flex;align-items:center;gap:8px">
            <span class="service-name">${x.name}</span>
            <span class="badge ${state}">${label}</span>
          </div>
          <div style="margin-top:4px">
            <span class="meta-tag">Port ${x.port}</span>
            <span class="meta-tag">${x.process_running ? 'Process ✓' : 'Process ✗'}</span>
            <span class="meta-tag">${x.port_listening  ? 'Port ✓'    : 'Port ✗'}</span>
          </div>
        </div>${btn}
      </div>`;
    }).join('');
  } catch(e) {}
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
