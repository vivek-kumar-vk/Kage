@echo off
REM Detached full Finance OS V1 build. Survives the Claude session / terminal closing.
REM
REM   run_build_all.bat          -> RESUME: keeps finance-os/, skips already-green phases
REM   run_build_all.bat fresh    -> wipe finance-os/ + progress, build from phase 0
REM
REM Launch detached:
REM   powershell -Command "Start-Process -WindowStyle Hidden 'B:\inky_code\.scratch\finance-os-build\run_build_all.bat'"
REM Check progress:  type B:\inky_code\.scratch\finance-os-build\progress\_run.log
REM Final result:    type B:\inky_code\.scratch\finance-os-build\progress\RUN_REPORT.md
cd /d B:\inky_code

REM 1. llama-server up? if not, start it.
curl -s -o nul http://127.0.0.1:8080/health
if errorlevel 1 (
  start "" /b C:\inky_models\bin\llama-server.exe --model C:/inky_models/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf --alias qwen2.5-coder-7b-instruct-q5_k_m --host 127.0.0.1 --port 8080 --threads 6 --ctx-size 24576 --parallel 1 --n-gpu-layers 28 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0
  timeout /t 40 /nobreak >nul
)

REM 2. fresh mode only: clean slate
if /i "%~1"=="fresh" (
  if exist finance-os rmdir /s /q finance-os
  del /q .scratch\finance-os-build\progress\phase*-progress.md 2>nul
  del /q .scratch\lm-ui-gaps\ledger.md 2>nul
)
del /q .scratch\finance-os-build\progress\RUN_REPORT.md 2>nul

REM 3. the run (all 9 phases; a re-launch without "fresh" skips already-green phases)
python .scratch\finance-os-build\run_build.py ^
  .scratch\finance-os-build\manifests\phase0.json ^
  .scratch\finance-os-build\manifests\phase1.json ^
  .scratch\finance-os-build\manifests\phase2.json ^
  .scratch\finance-os-build\manifests\phase3.json ^
  .scratch\finance-os-build\manifests\phase4.json ^
  .scratch\finance-os-build\manifests\phase5.json ^
  .scratch\finance-os-build\manifests\phase6.json ^
  .scratch\finance-os-build\manifests\phase7.json ^
  .scratch\finance-os-build\manifests\phase8.json  > .scratch\finance-os-build\progress\_run.log 2>&1
