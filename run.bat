@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0run.py" %*
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0run.py" %*
    exit /b %errorlevel%
)

echo [ERROR] Python 3.10+ not found in PATH.
exit /b 1