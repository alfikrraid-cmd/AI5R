@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n Docker volume restore
REM Restores the n8n data volume from a .tar.gz produced by
REM backup-volume.bat.
REM
REM DESTRUCTIVE: this replaces all current data in the volume
REM (workflows, credentials, execution history, settings) with
REM the contents of the chosen backup archive.
REM ============================================================

set CONTAINER_NAME=ai5r-n8n
set SCRIPT_DIR=%~dp0
set BACKUP_DIR=%SCRIPT_DIR%BACKUPS

if "%~1"=="" (
    echo Usage: restore-volume.bat ^<backup-filename-in-BACKUPS-folder^>
    echo.
    echo Available backups:
    dir /b "%BACKUP_DIR%\*.tar.gz" 2>nul
    exit /b 1
)

set ARCHIVE_NAME=%~1
set ARCHIVE_PATH=%BACKUP_DIR%\%ARCHIVE_NAME%

if not exist "%ARCHIVE_PATH%" (
    echo [ERROR] Backup file not found: %ARCHIVE_PATH%
    exit /b 1
)

docker inspect %CONTAINER_NAME% >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Container "%CONTAINER_NAME%" not found.
    exit /b 1
)

set N8N_VOLUME=
for /f "delims=" %%v in ('docker inspect %CONTAINER_NAME% --format "{{range .Mounts}}{{.Name}}{{end}}"') do set N8N_VOLUME=%%v
if "%N8N_VOLUME%"=="" (
    echo [ERROR] Could not determine the n8n data volume from container "%CONTAINER_NAME%".
    exit /b 1
)

echo WARNING: This will REPLACE all current data in volume "%N8N_VOLUME%"
echo with the contents of %ARCHIVE_NAME%.
echo Current workflows, credentials, and execution history will be overwritten.
set /p CONFIRM=Type YES to continue:
if /i not "%CONFIRM%"=="YES" (
    echo Restore cancelled.
    exit /b 0
)

echo Stopping container "%CONTAINER_NAME%" ...
docker stop %CONTAINER_NAME% >nul

echo Restoring volume "%N8N_VOLUME%" from %ARCHIVE_NAME% ...
docker run --rm -v %N8N_VOLUME%:/data -v "%BACKUP_DIR%":/backup alpine sh -c "find /data -mindepth 1 -delete && tar xzf /backup/%ARCHIVE_NAME% -C /data"

if errorlevel 1 (
    echo [ERROR] Restore failed. Volume may be in an inconsistent state.
    echo Starting container back up ...
    docker start %CONTAINER_NAME% >nul
    exit /b 1
)

echo Starting container "%CONTAINER_NAME%" ...
docker start %CONTAINER_NAME% >nul

echo [OK] Volume restored from %ARCHIVE_NAME%. Container restarted.
endlocal
