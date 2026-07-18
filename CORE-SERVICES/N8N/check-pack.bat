@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n Workflow Pack Integrity Checker
REM Runs the full integrity check across all current packs:
REM required files, manifest schema, registry.json consistency,
REM referenced workflow files, BACKUPS structure, duplicate
REM workflow ids, duplicate filenames, invalid manifestVersion.
REM
REM Delegates to validate-workflows.ps1 and update-registry.ps1
REM (dry-run) rather than duplicating their checks. Offline --
REM does not call the n8n REST API, and never writes to the real
REM registry.json.
REM ============================================================

set SCRIPT_DIR=%~dp0
set N8N_DIR=%SCRIPT_DIR:~0,-1%
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

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%check-pack.ps1" -Pack "%PACK%" -N8nDir "%N8N_DIR%"
exit /b %ERRORLEVEL%
