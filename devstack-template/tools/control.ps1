param(
    [string]$Action = "status",
    [string]$Service = "all"
)

$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot

function Start-Svc {
    param([string]$Name,[string]$File,[string[]]$Args)
    if (Test-Path -LiteralPath $File) {
        $workDir = Split-Path -Parent $File
        Start-Process -WindowStyle Hidden -WorkingDirectory $workDir -FilePath $File -ArgumentList $Args | Out-Null
        "started:$Name"
    }
}

function Stop-Svc {
    param([string]$Name)
    switch ($Name) {
        "apache" { & "$root\apache\bin\httpd.exe" -k shutdown -d "$root\apache" | Out-Null }
        "nginx" { & "$root\nginx\nginx.exe" -p "$root\nginx" -s quit | Out-Null }
        "php" { taskkill /f /im php-cgi.exe | Out-Null }
        "mysql" { taskkill /f /im mysqld.exe | Out-Null }
    }
    "stopped:$Name"
}

function Restart-Svc {
    param([string]$Name)
    Stop-Svc $Name | Out-Null
    Start-Sleep -Milliseconds 600
    switch ($Name) {
        "mysql" { Start-Svc "mysql" "$root\mysql\bin\mysqld.exe" @("--defaults-file=$root\mysql\my.ini") | Out-Null }
        "php" { Start-Svc "php" "$root\php\php-cgi.exe" @("-b","127.0.0.1:9000","-c","$root\php\php.ini") | Out-Null }
        "apache" { Start-Svc "apache" "$root\apache\bin\httpd.exe" @("-d","$root\apache") | Out-Null }
        "nginx" { Start-Svc "nginx" "$root\nginx\nginx.exe" @("-p","$root\nginx") | Out-Null }
    }
    "restarted:$Name"
}

switch ($Action.ToLower()) {
    "start" {
        if ($Service -eq "all") {
            Start-Svc "mysql" "$root\mysql\bin\mysqld.exe" @("--defaults-file=$root\mysql\my.ini")
            Start-Svc "php" "$root\php\php-cgi.exe" @("-b","127.0.0.1:9000","-c","$root\php\php.ini")
            Start-Svc "apache" "$root\apache\bin\httpd.exe" @("-d","$root\apache")
            Start-Svc "nginx" "$root\nginx\nginx.exe" @("-p","$root\nginx")
        } else {
            switch ($Service) {
                "mysql" { Start-Svc "mysql" "$root\mysql\bin\mysqld.exe" @("--defaults-file=$root\mysql\my.ini") | Out-Null }
                "php" { Start-Svc "php" "$root\php\php-cgi.exe" @("-b","127.0.0.1:9000","-c","$root\php\php.ini") | Out-Null }
                "apache" { Start-Svc "apache" "$root\apache\bin\httpd.exe" @("-d","$root\apache") | Out-Null }
                "nginx" { Start-Svc "nginx" "$root\nginx\nginx.exe" @("-p","$root\nginx") | Out-Null }
            }
        }
        "ok"
    }
    "stop" {
        if ($Service -eq "all") {
            Stop-Svc "apache" | Out-Null
            Stop-Svc "nginx" | Out-Null
            Stop-Svc "php" | Out-Null
            Stop-Svc "mysql" | Out-Null
        } else {
            Stop-Svc $Service | Out-Null
        }
        "ok"
    }
    "restart" {
        if ($Service -eq "all") {
            Stop-Svc "apache" | Out-Null
            Stop-Svc "nginx" | Out-Null
            Stop-Svc "php" | Out-Null
            Stop-Svc "mysql" | Out-Null
            Start-Sleep -Milliseconds 900
            Start-Svc "mysql" "$root\mysql\bin\mysqld.exe" @("--defaults-file=$root\mysql\my.ini") | Out-Null
            Start-Svc "php" "$root\php\php-cgi.exe" @("-b","127.0.0.1:9000","-c","$root\php\php.ini") | Out-Null
            Start-Svc "apache" "$root\apache\bin\httpd.exe" @("-d","$root\apache") | Out-Null
            Start-Svc "nginx" "$root\nginx\nginx.exe" @("-p","$root\nginx") | Out-Null
        } else {
            Restart-Svc $Service | Out-Null
        }
        "ok"
    }
    default {
        "ok"
    }
}
