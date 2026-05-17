@echo off
setlocal
title DevStack - Starting Services
cd /d "%~dp0"

echo ======================================
echo   DevStack - Starting Portable Stack
echo ======================================
echo.

if not exist "mysql\bin\mysqld.exe" (
    echo [WARN] MariaDB binary not found at mysql\bin\mysqld.exe
) else (
    echo [1/4] Starting MariaDB...
    powershell -NoProfile -Command "Start-Process -WindowStyle Minimized -FilePath '%CD%\\mysql\\bin\\mysqld.exe' -ArgumentList '--defaults-file=%CD%\\mysql\\my.ini'"
    timeout /t 2 /nobreak >nul
)

if not exist "php\php-cgi.exe" (
    echo [WARN] PHP-CGI not found at php\php-cgi.exe
) else (
    echo [2/4] Starting PHP FastCGI on 127.0.0.1:9000...
    powershell -NoProfile -Command "Start-Process -WindowStyle Minimized -FilePath '%CD%\\php\\php-cgi.exe' -ArgumentList '-b 127.0.0.1:9000 -c %CD%\\php\\php.ini'"
    timeout /t 1 /nobreak >nul
)

if not exist "apache\bin\httpd.exe" (
    echo [WARN] Apache binary not found at apache\bin\httpd.exe
) else (
    echo [3/4] Starting Apache...
    powershell -NoProfile -Command "Start-Process -WindowStyle Minimized -FilePath '%CD%\\apache\\bin\\httpd.exe' -ArgumentList '-d %CD%\\apache'"
    timeout /t 2 /nobreak >nul
)

if not exist "nginx\nginx.exe" (
    echo [INFO] Nginx not found ^(optional^). Skipping.
) else (
    echo [4/4] Starting Nginx...
    powershell -NoProfile -Command "Start-Process -WindowStyle Minimized -FilePath '%CD%\\nginx\\nginx.exe' -ArgumentList '-p %CD%\\nginx'"
)

echo.
echo Done. Open dashboard:
echo   http://localhost/dashboard/
echo.
if /I "%~1"=="--no-pause" goto :eof
pause
endlocal
