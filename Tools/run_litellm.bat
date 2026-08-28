@echo off
REM Windows wrapper for Tools\run_litellm.py - referenced by
REM Start_Inky\Start_Everything.bat. All the logic is in the .py so the
REM phone host can run the same thing without a .bat.
setlocal
cd /d "%~dp0.."
set "VPY=%CD%\.venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo .venv not found. Run Start_Inky\Start_Everything.bat once first.
  exit /b 1
)
"%VPY%" "%CD%\Tools\run_litellm.py" %*
