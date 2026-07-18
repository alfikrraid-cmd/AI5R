@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM AI5R - n8n Workflow Registry: update
REM Scans WORKFLOWS\*\manifest.json and regenerates registry.json
REM at the root of this folder. Offline -- does not call the n8n
REM REST API.
REM
REM Validates each pack manifest for:
REM   - missing manifest.json
REM   - malformed JSON
REM   - invalid manifestVersion
REM   - duplicate pack name
REM   - duplicate workflow entry (same workflow in >1 pack)
REM
REM If any pack fails validation, registry.json is left untouched
REM and this script exits non-zero.
REM ============================================================

set SCRIPT_DIR=%~dp0
set WORKFLOWS_DIR=%SCRIPT_DIR%WORKFLOWS
set REGISTRY_PATH=%SCRIPT_DIR%registry.json

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%update-registry.ps1" -WorkflowsDir "%WORKFLOWS_DIR%" -RegistryPath "%REGISTRY_PATH%"
exit /b %ERRORLEVEL%
