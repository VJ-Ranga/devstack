<?php
/**
 * DevStack Status API — lightweight JSON endpoint.
 * Polled by the portal + dashboard JS every 5 s instead of full page reloads.
 *
 * Returns: { services[], generated_at, machine, php_version, site_count }
 */
declare(strict_types=1);
header('Content-Type: application/json');
header('Cache-Control: no-store');

$stackRoot    = realpath(__DIR__ . '/../../');
$statusScript = $stackRoot . '/tools/status.ps1';

$payload = ['services' => [], 'generated_at' => '', 'machine' => '', 'php_version' => '', 'site_count' => 0];

// Service status from PowerShell
if (is_file($statusScript)) {
    $json    = shell_exec('powershell -NoProfile -ExecutionPolicy Bypass -File ' . escapeshellarg($statusScript));
    $decoded = is_string($json) ? json_decode($json, true) : null;
    if (is_array($decoded)) {
        $payload = array_merge($payload, $decoded);
    }
}

// PHP version (this script runs under the active PHP, so it's accurate)
$payload['php_version'] = PHP_VERSION;

// Count local sites (htdocs subfolders, excluding system folders)
$htdocs   = $stackRoot . '/htdocs';
$excluded = ['dashboard', 'phpmyadmin', 'assets'];
$count    = 0;
foreach (scandir($htdocs) ?: [] as $entry) {
    if ($entry[0] === '.' || in_array($entry, $excluded, true)) continue;
    if (is_dir($htdocs . '/' . $entry)) $count++;
}
$payload['site_count'] = $count;

echo json_encode($payload);
