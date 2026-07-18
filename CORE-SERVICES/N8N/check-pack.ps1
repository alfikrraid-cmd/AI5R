param(
    [string]$Pack,
    [Parameter(Mandatory = $true)][string]$N8nDir
)

# ============================================================
# AI5R - n8n Workflow Pack Integrity Checker
#
# Orchestrates the EXISTING validators rather than reimplementing
# their checks:
#   - validate-workflows.ps1 -> required per-pack files, referenced
#     workflow files exist, workflow JSON required keys (name/nodes)
#   - update-registry.ps1 (dry-run into a temp file) -> invalid
#     manifestVersion, duplicate pack names, duplicate workflow ids,
#     malformed JSON
#
# This script owns only the checks neither of those already perform:
#   - required top-level service files
#   - manifest.json top-level schema keys
#   - registry.json consistency (committed vs. freshly regenerated)
#   - BACKUPS/ folder structure
#   - duplicate workflow FILENAMES across packs (id-based dedup in
#     update-registry.ps1 does not catch same-file/different-id
#     collisions)
#
# Fails closed: any section failure -> overall FAIL, exit 1. Never
# writes to the real registry.json (regenerates into a temp path
# only, for comparison).
# ============================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkflowsDir = Join-Path $N8nDir "WORKFLOWS"
$RegistryPath = Join-Path $N8nDir "registry.json"
$BackupsDir = Join-Path $N8nDir "BACKUPS"

$overallPass = $true
$section = [ordered]@{}

function Set-Section([string]$name, [bool]$pass) {
    if ($section.Contains($name)) {
        $section[$name] = $section[$name] -and $pass
    }
    else {
        $section[$name] = $pass
    }
    if (-not $pass) { $script:overallPass = $false }
}

Write-Host "=== MWO-N8N-005 Workflow Pack Integrity Checker ==="
Write-Host "N8N root: $N8nDir"

# ------------------------------------------------------------------
# 1. Required top-level service files
# ------------------------------------------------------------------
Write-Host ""
Write-Host "--- Required files ---"
$reqPass = $true
$requiredFiles = @(
    "docker-compose.yml",
    "README.md",
    "credentials.example.md",
    "registry.json",
    (Join-Path "WORKFLOWS" "manifest.json"),
    (Join-Path "BACKUPS" ".gitignore"),
    (Join-Path "BACKUPS" ".gitkeep")
)
foreach ($f in $requiredFiles) {
    $p = Join-Path $N8nDir $f
    if (Test-Path $p) {
        Write-Host "[OK] required file present: $f"
    }
    else {
        Write-Host "[FAIL] required file missing: $f"
        $reqPass = $false
    }
}
Set-Section "required-files" $reqPass

# ------------------------------------------------------------------
# 2. BACKUPS/ structure (not covered by any existing script)
# ------------------------------------------------------------------
Write-Host ""
Write-Host "--- BACKUPS structure ---"
$backupsPass = $true
$gitignorePath = Join-Path $BackupsDir ".gitignore"
if (Test-Path $gitignorePath) {
    $giContent = Get-Content $gitignorePath -Raw
    foreach ($token in @("*.tar.gz", "!.gitkeep")) {
        if ($giContent -notlike "*$token*") {
            Write-Host "[FAIL] BACKUPS/.gitignore missing expected rule: $token"
            $backupsPass = $false
        }
    }
    if ($backupsPass) { Write-Host "[OK] BACKUPS/.gitignore rules look correct" }
}
else {
    Write-Host "[FAIL] BACKUPS/.gitignore missing"
    $backupsPass = $false
}
Set-Section "backups-structure" $backupsPass

# ------------------------------------------------------------------
# 3. Delegated: validate-workflows.ps1
#    (required per-pack files, referenced workflow files exist,
#    workflow JSON required keys)
# ------------------------------------------------------------------
Write-Host ""
Write-Host "--- Pack file/schema validation (delegated: validate-workflows.ps1) ---"
$validateScript = Join-Path $ScriptDir "validate-workflows.ps1"
$vSplat = @{ WorkflowsDir = $WorkflowsDir }
if ($Pack) { $vSplat.Pack = $Pack }
try {
    & $validateScript @vSplat
    Set-Section "pack-files-and-schema" ($LASTEXITCODE -eq 0)
}
catch {
    Write-Host "[FAIL] validate-workflows.ps1 could not run: $($_.Exception.Message)"
    Set-Section "pack-files-and-schema" $false
}

# ------------------------------------------------------------------
# 4. Manifest schema: required top-level keys (not covered by
#    validate-workflows.ps1, which only checks workflow JSON keys,
#    or update-registry.ps1, which only checks manifestVersion)
# ------------------------------------------------------------------
Write-Host ""
Write-Host "--- Manifest schema (top-level keys) ---"
$schemaPass = $true
$requiredKeys = @("pack", "n8nTag", "lastExportAt", "workflows")
$packDirs = @()
try {
    $packDirs = Get-ChildItem -Path $WorkflowsDir -Directory
}
catch {
    Write-Host "[FAIL] cannot list pack directories under $WorkflowsDir : $($_.Exception.Message)"
    $schemaPass = $false
}
foreach ($dir in $packDirs) {
    $manifestPath = Join-Path $dir.FullName "manifest.json"
    if (-not (Test-Path $manifestPath)) { continue }   # already reported above
    try {
        $m = Get-Content $manifestPath -Raw | ConvertFrom-Json
    }
    catch {
        continue   # malformed JSON already reported by update-registry.ps1 below
    }
    $propNames = $m.PSObject.Properties.Name
    foreach ($k in $requiredKeys) {
        if ($propNames -notcontains $k) {
            Write-Host "[FAIL] $($dir.Name)/manifest.json missing required key: $k"
            $schemaPass = $false
        }
    }
}
if ($schemaPass) { Write-Host "[OK] all pack manifests contain required top-level keys" }
Set-Section "manifest-schema" $schemaPass

# ------------------------------------------------------------------
# 5. Delegated: update-registry.ps1, dry-run into a temp file
#    (invalid manifestVersion, duplicate pack, duplicate workflow
#    ids, malformed JSON) + registry.json consistency (new: diff
#    committed registry.json against a fresh regeneration)
# ------------------------------------------------------------------
Write-Host ""
Write-Host "--- Registry validation (delegated: update-registry.ps1, dry-run) ---"
$updateScript = Join-Path $ScriptDir "update-registry.ps1"
$tempRegistry = Join-Path ([System.IO.Path]::GetTempPath()) ("registry-check-{0}.json" -f ([guid]::NewGuid()))
try {
    & $updateScript -WorkflowsDir $WorkflowsDir -RegistryPath $tempRegistry
    $registryValid = ($LASTEXITCODE -eq 0)
    Set-Section "manifest-version-and-duplicates" $registryValid

    Write-Host ""
    Write-Host "--- Registry consistency ---"
    if (-not $registryValid) {
        Write-Host "[FAIL] registry regeneration failed validation -- skipping consistency comparison"
        Set-Section "registry-consistency" $false
    }
    elseif (-not (Test-Path $RegistryPath)) {
        Write-Host "[FAIL] registry.json missing at $RegistryPath -- cannot check consistency"
        Set-Section "registry-consistency" $false
    }
    else {
        $committed = Get-Content $RegistryPath -Raw | ConvertFrom-Json
        $fresh = Get-Content $tempRegistry -Raw | ConvertFrom-Json
        $committed.PSObject.Properties.Remove("generatedAt")
        $fresh.PSObject.Properties.Remove("generatedAt")
        $committedJson = $committed | ConvertTo-Json -Depth 100
        $freshJson = $fresh | ConvertTo-Json -Depth 100
        if ($committedJson -eq $freshJson) {
            Write-Host "[OK] registry.json is in sync with WORKFLOWS/*/manifest.json"
            Set-Section "registry-consistency" $true
        }
        else {
            Write-Host "[FAIL] registry.json is stale -- run update-registry.bat to refresh"
            Set-Section "registry-consistency" $false
        }
    }
}
catch {
    Write-Host "[FAIL] update-registry.ps1 could not run: $($_.Exception.Message)"
    Set-Section "manifest-version-and-duplicates" $false
    Set-Section "registry-consistency" $false
}
finally {
    Remove-Item -Path $tempRegistry -ErrorAction SilentlyContinue
}

# ------------------------------------------------------------------
# 6. Duplicate workflow FILENAMES across packs (new: update-registry
#    keys duplicates by id first, so a same-file/different-id
#    collision across packs is not caught there)
# ------------------------------------------------------------------
Write-Host ""
Write-Host "--- Duplicate filenames across packs ---"
$dupFilePass = $true
$fileOwners = @{}
foreach ($dir in $packDirs) {
    $manifestPath = Join-Path $dir.FullName "manifest.json"
    if (-not (Test-Path $manifestPath)) { continue }
    try {
        $m = Get-Content $manifestPath -Raw | ConvertFrom-Json
    }
    catch {
        continue
    }
    foreach ($wf in @($m.workflows)) {
        if (-not $wf.file) { continue }
        if ($fileOwners.ContainsKey($wf.file)) {
            Write-Host "[FAIL] duplicate filename '$($wf.file)' used by both $($fileOwners[$wf.file]) and $($dir.Name)"
            $dupFilePass = $false
        }
        else {
            $fileOwners[$wf.file] = $dir.Name
        }
    }
}
if ($dupFilePass) { Write-Host "[OK] no duplicate filenames across packs" }
Set-Section "duplicate-filenames" $dupFilePass

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
Write-Host ""
Write-Host "=== SUMMARY ==="
foreach ($key in $section.Keys) {
    $status = if ($section[$key]) { "PASS" } else { "FAIL" }
    Write-Host ("  [{0}] {1}" -f $status, $key)
}

Write-Host ""
if ($overallPass) {
    Write-Host "[OK] INTEGRITY CHECK PASSED"
    exit 0
}
else {
    Write-Host "[FAIL] INTEGRITY CHECK FAILED"
    exit 1
}
