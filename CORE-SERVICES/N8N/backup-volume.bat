@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n Docker volume backup
REM Backs up the entire n8n data volume (workflows, credentials,
REM execution history, settings) into a timestamped .tar.gz under
REM CORE-SERVICES\N8N\BACKUPS\
REM
REM The volume name is discovered dynamically from the running
REM container's mounts, so this works regardless of the Docker
REM Compose project name prefix.
REM ============================================================

set CONTAINER_NAME=ai5r-n8n
set SCRIPT_DIR=%~dp0
set BACKUP_DIR=%SCRIPT_DIR%BACKUPS

if not exist "%BACKUP_DIR%" (
    echo [ERROR] Backup directory not found: %BACKUP_DIR%
    exit /b 1
)

docker inspect %CONTAINER_NAME% >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Container "%CONTAINER_NAME%" not found. Is it running?
    exit /b 1
)

set N8N_VOLUME=
for /f "delims=" %%v in ('docker inspect %CONTAINER_NAME% --format "{{range .Mounts}}{{.Name}}{{end}}"') do set N8N_VOLUME=%%v
if "%N8N_VOLUME%"=="" (
    echo [ERROR] Could not determine the n8n data volume from container "%CONTAINER_NAME%".
    exit /b 1
)

set TIMESTAMP=
for /f "delims=" %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TIMESTAMP=%%t
set ARCHIVE_NAME=n8n_data_%TIMESTAMP%.tar.gz

echo Backing up volume "%N8N_VOLUME%" to %ARCHIVE_NAME% ...
docker run --rm -v %N8N_VOLUME%:/data -v "%BACKUP_DIR%":/backup alpine sh -c "cd /data && tar czf /backup/%ARCHIVE_NAME% ."

if errorlevel 1 (
    echo [ERROR] Backup failed.
    exit /b 1
)

echo [OK] Volume backup saved to: %BACKUP_DIR%\%ARCHIVE_NAME%
endlocal
