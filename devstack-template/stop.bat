@echo off
setlocal
title DevStack - Stopping Services
cd /d "%~dp0"

echo ======================================
echo   DevStack - Stopping Portable Stack
echo ======================================
echo.

if exist "apache\bin\httpd.exe" (
    apache\bin\httpd.exe -k shutdown -d "%~dp0apache" 2>nul
    echo [OK] Apache stop signal sent
)

if exist "nginx\nginx.exe" (
    nginx\nginx.exe -p "%~dp0nginx" -s quit 2>nul
    echo [OK] Nginx stop signal sent
)

taskkill /f /im php-cgi.exe >nul 2>nul
echo [OK] PHP-CGI stopped (if running)

if exist "mysql\bin\mysqladmin.exe" (
    mysql\bin\mysqladmin.exe -u root shutdown >nul 2>nul
)
taskkill /f /im mysqld.exe >nul 2>nul
echo [OK] MariaDB stopped (if running)

echo.
echo All stop commands completed.
if /I "%~1"=="--no-pause" goto :eof
pause
endlocal
