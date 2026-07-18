@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n Workflow Pack Manager: validate
REM Checks every pack's manifest.json against the workflow JSON
REM files on disk (valid JSON, required keys, no drift). Offline --
REM does not call the n8n REST API.
REM ============================================================

set SCRIPT_DIR=%~dp0
set WORKFLOWS_DIR=%SCRIPT_DIR%WORKFLOWS
set VALID_PACKS=COMMON LTSA AUDITOR SCHOOL UMKM

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

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%validate-workflows.ps1" -Pack "%PACK%" -WorkflowsDir "%WORKFLOWS_DIR%"
exit /b %ERRORLEVEL%
