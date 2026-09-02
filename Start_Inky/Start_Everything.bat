@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

REM ===================================================================
REM  START EVERYTHING
REM
REM  Double-click this file. It will:
REM    1. create a private .venv folder the first time
REM    2. install what every screen needs
REM    3. start all the screens at once
REM
REM  Nothing is installed into your system Python.
REM  Press Ctrl+C in this window to stop everything.
REM ===================================================================

set "PROJECT=%CD%"
set "VENV=%PROJECT%\.venv"
set "VPY=%VENV%\Scripts\python.exe"
set "BASE="

REM --- find a Python to build the private folder with ----------------
REM The py launcher picks the newest compatible version.
where py >nul 2>&1 && (
    for %%V in (3.13 3.12 3.11) do (
        py -%%V --version >nul 2>&1 && if not defined BASE set "BASE=py -%%V"
    )
)
if defined BASE goto :havepy
where py >nul 2>&1 && set "BASE=py"
if defined BASE goto :havepy
where python >nul 2>&1 && set "BASE=python"
if defined BASE goto :havepy
set "KNOWN=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if exist "%KNOWN%" set "BASE=%KNOWN%"
if not defined BASE goto :nopython

:havepy
echo Using Python: %BASE%
%BASE% --version

REM --- create .venv on first run only --------------------------------
if exist "%VPY%" goto :haveenv
echo.
echo Creating a private Python folder in .venv  (first run only)
%BASE% -m venv "%VENV%"
if errorlevel 1 goto :fail

:haveenv
REM --- install what the screens need --------------------------------
"%VPY%" -m pip show fastapi >nul 2>&1
if not errorlevel 1 goto :run

:install
echo.
echo Installing what the screens need  (first run only, takes a minute)
"%VPY%" -m pip install --upgrade pip --quiet



REM Every screen keeps its own list of what it needs. Install all of
REM them, whatever they are called - no screen is named in this file.
for /d %%S in ("%PROJECT%\Screens\*") do (
    for %%R in ("%%S\Setup\requirements_*.txt") do (
        echo   from %%~nxR
        "%VPY%" -m pip install -r "%%R" --quiet
        if errorlevel 1 goto :fail
    )
)

REM The menu you land on keeps its own list too.
for %%R in ("%PROJECT%\Main_Menu\Setup\requirements_*.txt") do (
    echo   from %%~nxR
    "%VPY%" -m pip install -r "%%R" --quiet
    if errorlevel 1 goto :fail
)

:run
echo.
REM --- the model gateway, in its own window --------------------------
REM The Model screen reports on it. Safe when already running - the
REM launcher just says so and leaves the gateway alone.
start "OmniRoute gateway" "%VPY%" "%PROJECT%\Start_Inky\run_omniroute.py"
timeout /t 2 /nobreak >nul
REM --- the market-data MCP server, in its own window -----------------
REM Tool seam for the Agent Deck research agents (port 3101). Safe when
REM already running - the launcher just says so and leaves it alone.
start "Market MCP" "%VPY%" "%PROJECT%\Start_Inky\run_market_mcp.py"
timeout /t 2 /nobreak >nul
"%VPY%" "%PROJECT%\Start_Inky\start_every_screen.py"
if errorlevel 1 goto :fail
goto :done

:nopython
echo.
echo -------------------------------------------------------------------
echo Python was not found.
echo.
echo Neither "py" nor "python" is on your PATH, and nothing was at:
echo   %LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe
echo.
echo Fix: open this file in Notepad and set BASE to the full path of
echo your python.exe
echo -------------------------------------------------------------------
pause
exit /b 1

:fail
echo.
echo -------------------------------------------------------------------
echo Something failed. The error is the message just above this box.
echo -------------------------------------------------------------------
pause
exit /b 1

:done
pause
