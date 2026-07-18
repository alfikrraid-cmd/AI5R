@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n workflow export
REM Exports every workflow from the running n8n container as
REM individual JSON files into CORE-SERVICES\N8N\WORKFLOWS\
REM ============================================================

set CONTAINER_NAME=ai5r-n8n
set SCRIPT_DIR=%~dp0
set WORKFLOWS_DIR=%SCRIPT_DIR%WORKFLOWS
set EXPORT_TMP=/tmp/n8n_workflow_export

docker inspect %CONTAINER_NAME% >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Container "%CONTAINER_NAME%" not found. Is it running?
    exit /b 1
)

if not exist "%WORKFLOWS_DIR%" (
    echo [ERROR] Workflows directory not found: %WORKFLOWS_DIR%
    exit /b 1
)

echo Exporting workflows from "%CONTAINER_NAME%" ...
docker exec %CONTAINER_NAME% sh -c "rm -rf %EXPORT_TMP% && mkdir -p %EXPORT_TMP% && n8n export:workflow --all --separate --output=%EXPORT_TMP%"
if errorlevel 1 (
    echo [ERROR] n8n export:workflow failed.
    exit /b 1
)

docker cp %CONTAINER_NAME%:%EXPORT_TMP%/. "%WORKFLOWS_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to copy exported workflows out of the container.
    exit /b 1
)

docker exec %CONTAINER_NAME% rm -rf %EXPORT_TMP%

echo [OK] Workflows exported to: %WORKFLOWS_DIR%
endlocal
