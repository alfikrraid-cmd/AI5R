param(
    [Parameter(Mandatory = $true)][string]$WorkflowsDir,
    [Parameter(Mandatory = $true)][string]$RegistryPath
)

$ErrorActionPreference = "Stop"
$SupportedManifestVersion = 1

$overallPass = $true
$packEntries = [ordered]@{}
$seenPackNames = @{}   # pack name -> folder that first declared it
$seenWorkflows = @{}   # workflow id/file -> pack that first listed it

$packDirs = Get-ChildItem -Path $WorkflowsDir -Directory | Sort-Object Name

foreach ($dir in $packDirs) {
    $folderName = $dir.Name
    $manifestPath = Join-Path $dir.FullName "manifest.json"

    Write-Host ""
    Write-Host "=== Scanning $folderName ==="

    if (-not (Test-Path $manifestPath)) {
        Write-Host "[FAIL] $folderName : missing manifest.json"
        $overallPass = $false
        continue
    }

    try {
        $m = Get-Content $manifestPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-Host "[FAIL] $folderName : manifest.json is malformed JSON: $($_.Exception.Message)"
        $overallPass = $false
        continue
    }

    $packName = if ($m.pack) { $m.pack } else { $folderName }

    if ($seenPackNames.ContainsKey($packName)) {
        Write-Host "[FAIL] $folderName : duplicate pack '$packName' (already declared by $($seenPackNames[$packName])/manifest.json)"
        $overallPass = $false
        continue
    }
    $seenPackNames[$packName] = $folderName

    if ($null -ne $m.manifestVersion -and $m.manifestVersion -ne $SupportedManifestVersion) {
        Write-Host "[FAIL] $folderName : invalid manifestVersion '$($m.manifestVersion)' (expected $SupportedManifestVersion)"
        $overallPass = $false
        continue
    }

    $packOk = $true
    $workflows = @($m.workflows)
    foreach ($wf in $workflows) {
        $wfKey = if ($wf.id) { $wf.id } else { $wf.file }
        if (-not $wfKey) { continue }
        if ($seenWorkflows.ContainsKey($wfKey)) {
            Write-Host "[FAIL] $folderName : duplicate manifest entry '$wfKey' (already listed under $($seenWorkflows[$wfKey]))"
            $overallPass = $false
            $packOk = $false
            continue
        }
        $seenWorkflows[$wfKey] = $packName
    }

    if (-not $packOk) { continue }

    $packEntries[$packName] = [ordered]@{
        pack            = $packName
        folder          = $folderName
        manifestPath    = "WORKFLOWS/$folderName/manifest.json"
        manifestVersion = $m.manifestVersion
        n8nTag          = $m.n8nTag
        workflowCount   = $workflows.Count
        lastExportAt    = $m.lastExportAt
    }

    Write-Host "[OK] $folderName : $($workflows.Count) workflow(s), pack '$packName'"
}

Write-Host ""
if ($overallPass) {
    $registry = [ordered]@{
        version     = 1
        description = "AI5R n8n Workflow Registry. Generated index aggregating every pack manifest under WORKFLOWS/. Regenerate with update-registry.bat -- do not hand-edit."
        generatedAt = (Get-Date).ToString("o")
        packs       = $packEntries
    }
    $registry | ConvertTo-Json -Depth 100 | Set-Content -Path $RegistryPath -Encoding UTF8
    Write-Host "[OK] REGISTRY REGENERATED: $RegistryPath ($($packEntries.Count) pack(s))"
    exit 0
}
else {
    Write-Host "[FAIL] REGISTRY VALIDATION FAILED -- registry.json was NOT regenerated (existing file, if any, left untouched)"
    exit 1
}
