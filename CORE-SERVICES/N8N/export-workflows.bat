@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n Workflow Pack Manager: export
REM Pulls all workflows tagged with <PACK> from the n8n REST API
REM and writes them into WORKFLOWS\<PACK>\, updating manifest.json.
REM
REM Requires: n8n owner account + API key (Settings > API in n8n),
REM set via the N8N_API_KEY environment variable. N8N_URL defaults
REM to http://localhost:5678.
REM
REM Workflows are matched to a pack by n8n tag name == pack name.
REM Tag workflows in n8n (COMMON/LTSA/AUDITOR/SCHOOL/UMKM) first.
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
    echo Usage: export-workflows.bat ^<PACK^>
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

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%export-workflows.ps1" -Pack "%PACK%" -PackDir "%PACK_DIR%" -N8nUrl "%N8N_URL%" -ApiKey "%N8N_API_KEY%"
exit /b %ERRORLEVEL%
