$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $appDir "Run DevStack Manager.bat"
$icon = Join-Path $appDir "assets\icon.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "DevStack Manager.lnk"

if (-not (Test-Path -LiteralPath $target)) {
    throw "Launcher not found: $target"
}

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $appDir
if (Test-Path -LiteralPath $icon) {
    $shortcut.IconLocation = $icon
}
$shortcut.Save()

"Created shortcut: $shortcutPath"
