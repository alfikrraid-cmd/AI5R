@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n Workflow Pack Manager: import
REM Pushes every workflow recorded in WORKFLOWS\<PACK>\manifest.json
REM into n8n via the REST API (create if new, update if a workflow
REM with the same name already exists). Optionally activates them.
REM
REM Requires: N8N_API_KEY environment variable (see export-workflows.bat).
REM ============================================================

set SCRIPT_DIR=%~dp0
set WORKFLOWS_DIR=%SCRIPT_DIR%WORKFLOWS
set VALID_PACKS=COMMON LTSA AUDITOR SCHOOL UMKM
if "%N8N_URL%"=="" set N8N_URL=http://localhost:5678

if "%N8N_API_KEY%"=="" (
    echo [ERROR] N8N_API_KEY environment variable is not set.
    echo Generate one in n8n: Settings ^> API ^> Create an API Key
    echo Then: set N8N_API_KEY=your-key-here
    exit /b 1
)

set PACK=%~1
if "%PACK%"=="" (
    echo Usage: import-workflows.bat ^<PACK^> [--activate]
    echo Valid packs: %VALID_PACKS%
    exit /b 1
)

set PACK_VALID=0
for %%p in (%VALID_PACKS%) do (
    if /i "%%p"=="%PACK%" (
        set PACK_VALID=1
        set PACK=%%p
    )
)
if "%PACK_VALID%"=="0" (
    echo [ERROR] Unknown pack "%PACK%". Valid packs: %VALID_PACKS%
    exit /b 1
)

set PACK_DIR=%WORKFLOWS_DIR%\%PACK%
if not exist "%PACK_DIR%" (
    echo [ERROR] Pack directory not found: %PACK_DIR%
    exit /b 1
)

set ACTIVATE_FLAG=
if /i "%~2"=="--activate" set ACTIVATE_FLAG=-Activate

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%import-workflows.ps1" -Pack "%PACK%" -PackDir "%PACK_DIR%" -N8nUrl "%N8N_URL%" -ApiKey "%N8N_API_KEY%" %ACTIVATE_FLAG%
exit /b %ERRORLEVEL%
