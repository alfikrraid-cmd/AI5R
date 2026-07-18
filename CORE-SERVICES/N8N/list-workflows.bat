@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n Workflow Pack Manager: list
REM Lists workflows recorded in each pack's manifest.json (offline,
REM from disk). If N8N_API_KEY is set, also checks that the n8n
REM REST API is reachable.
REM ============================================================

set SCRIPT_DIR=%~dp0
set WORKFLOWS_DIR=%SCRIPT_DIR%WORKFLOWS
set VALID_PACKS=COMMON LTSA AUDITOR SCHOOL UMKM
if "%N8N_URL%"=="" set N8N_URL=http://localhost:5678

set PACK=%~1
if not "%PACK%"=="" (
    set PACK_VALID=0
    for %%p in (%VALID_PACKS%) do (
        if /i "%%p"=="%PACK%" (
            set PACK_VALID=1
            set PACK=%%p
        )
    )
    if "!PACK_VALID!"=="0" (
        echo [ERROR] Unknown pack "%PACK%". Valid packs: %VALID_PACKS%
        exit /b 1
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%list-workflows.ps1" -Pack "%PACK%" -WorkflowsDir "%WORKFLOWS_DIR%" -N8nUrl "%N8N_URL%" -ApiKey "%N8N_API_KEY%"
exit /b %ERRORLEVEL%
