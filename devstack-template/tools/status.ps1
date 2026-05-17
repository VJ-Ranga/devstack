param(
    [int]$apachePort = 8088,
    [int]$nginxPort = 80,
    [int]$phpPort = 9000,
    [int]$mysqlPort = 3306
)

$ErrorActionPreference = "SilentlyContinue"

function Test-Port {
    param([int]$Port)
    $conn = Get-NetTCPConnection -State Listen -LocalPort $Port | Select-Object -First 1
    return [bool]$conn
}

function Test-Process {
    param([string]$Name)
    $proc = Get-Process -Name $Name | Select-Object -First 1
    return [bool]$proc
}

$services = @(
    @{ key = "apache"; name = "Apache"; process = "httpd"; port = $apachePort },
    @{ key = "nginx"; name = "Nginx"; process = "nginx"; port = $nginxPort },
    @{ key = "php"; name = "PHP FastCGI"; process = "php-cgi"; port = $phpPort },
    @{ key = "mysql"; name = "MariaDB"; process = "mysqld"; port = $mysqlPort }
)

$result = @()
foreach ($svc in $services) {
    $procOk = Test-Process -Name $svc.process
    $portOk = Test-Port -Port $svc.port
    $state = if ($procOk -or $portOk) { "running" } else { "stopped" }

    $result += [PSCustomObject]@{
        key = $svc.key
        name = $svc.name
        process = $svc.process
        port = $svc.port
        process_running = $procOk
        port_listening = $portOk
        state = $state
    }
}

$payload = [PSCustomObject]@{
    generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    machine = $env:COMPUTERNAME
    services = $result
}

$payload | ConvertTo-Json -Depth 4
