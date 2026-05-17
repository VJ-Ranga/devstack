@echo off
setlocal

set "APP_DIR=%~dp0"
set "MAIN_PY=%APP_DIR%main.py"

if not exist "%MAIN_PY%" (
  echo Could not find main.py in:
  echo %APP_DIR%
  pause
  exit /b 1
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%MAIN_PY%"
  goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
  python "%MAIN_PY%"
  goto :end
)

echo Python was not found in PATH.
echo Install Python 3 and try again.
pause
exit /b 1

:end
if not %errorlevel%==0 (
  echo.
  echo App exited with an error.
  pause
)

endlocal
