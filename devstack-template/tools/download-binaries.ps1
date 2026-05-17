$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$downloadDir = Join-Path $root "_downloads"

if (-not (Test-Path -LiteralPath $downloadDir)) {
    New-Item -ItemType Directory -Path $downloadDir | Out-Null
}

function Download-FirstAvailable {
    param(
        [string]$Name,
        [string]$OutFile,
        [string[]]$Urls
    )

    $outPath = Join-Path $downloadDir $OutFile
    if (Test-Path -LiteralPath $outPath) {
        "[SKIP] $Name already downloaded: $OutFile"
        return $outPath
    }

    foreach ($url in $Urls) {
        try {
            "[TRY] $Name -> $url"
            Invoke-WebRequest -Uri $url -OutFile $outPath -UseBasicParsing -TimeoutSec 180
            if ((Get-Item $outPath).Length -gt 1024) {
                "[OK]  $Name downloaded: $OutFile"
                return $outPath
            }
        }
        catch {
            "[WARN] Failed URL for $Name"
        }
    }

    throw "Could not download $Name from known URLs."
}

$apache = Download-FirstAvailable -Name "Apache" -OutFile "apache.zip" -Urls @(
    "https://www.apachelounge.com/download/VS17/binaries/httpd-2.4.63-250207-win64-VS17.zip",
    "https://www.apachelounge.com/download/VS17/binaries/httpd-2.4.63-win64-VS17.zip",
    "https://www.apachelounge.com/download/VS17/binaries/httpd-2.4.62-win64-VS17.zip"
)

$php = Download-FirstAvailable -Name "PHP 8.4 TS" -OutFile "php.zip" -Urls @(
    "https://windows.php.net/downloads/releases/php-8.4.6-Win32-vs17-x64.zip",
    "https://windows.php.net/downloads/releases/php-8.4.5-Win32-vs17-x64.zip",
    "https://windows.php.net/downloads/releases/php-8.3.17-Win32-vs17-x64.zip"
)

$mariadb = Download-FirstAvailable -Name "MariaDB" -OutFile "mariadb.zip" -Urls @(
    "https://archive.mariadb.org/mariadb-11.7.2/winx64-packages/mariadb-11.7.2-winx64.zip",
    "https://archive.mariadb.org/mariadb-11.6.2/winx64-packages/mariadb-11.6.2-winx64.zip",
    "https://archive.mariadb.org/mariadb-11.5.2/winx64-packages/mariadb-11.5.2-winx64.zip"
)

$nginx = Download-FirstAvailable -Name "Nginx" -OutFile "nginx.zip" -Urls @(
    "https://nginx.org/download/nginx-1.27.4.zip",
    "https://nginx.org/download/nginx-1.26.2.zip"
)

""
"All downloads completed in: $downloadDir"
"- apache.zip"
"- php.zip"
"- mariadb.zip"
"- nginx.zip"
