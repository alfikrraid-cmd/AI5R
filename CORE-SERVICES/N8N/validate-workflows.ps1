param(
    [string]$Pack,
    [Parameter(Mandatory = $true)][string]$WorkflowsDir
)

$ErrorActionPreference = "Stop"
$packs = @("COMMON", "LTSA", "AUDITOR", "SCHOOL", "UMKM")
if ($Pack) { $packs = @($Pack) }

$overallPass = $true

foreach ($p in $packs) {
    $packDir = Join-Path $WorkflowsDir $p
    $manifestPath = Join-Path $packDir "manifest.json"
    Write-Host ""
    Write-Host "=== Validating $p ==="

    if (-not (Test-Path $packDir)) {
        Write-Host "[FAIL] pack directory missing: $packDir"
        $overallPass = $false
        continue
    }
    if (-not (Test-Path $manifestPath)) {
        Write-Host "[FAIL] manifest.json missing in $p"
        $overallPass = $false
        continue
    }

    try {
        $m = Get-Content $manifestPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-Host "[FAIL] manifest.json is not valid JSON: $($_.Exception.Message)"
        $overallPass = $false
        continue
    }

    $manifestFiles = @($m.workflows | ForEach-Object { $_.file })
    $diskFiles = @(Get-ChildItem -Path $packDir -Filter *.json | Where-Object { $_.Name -ne "manifest.json" } | ForEach-Object { $_.Name })

    $packPass = $true

    foreach ($f in $manifestFiles) {
        $fp = Join-Path $packDir $f
        if (-not (Test-Path $fp)) {
            Write-Host "[FAIL] $p : manifest references missing file: $f"
            $packPass = $false
            continue
        }
        try {
            $content = Get-Content $fp -Raw | ConvertFrom-Json
        }
        catch {
            Write-Host "[FAIL] $p/$f : invalid JSON"
            $packPass = $false
            continue
        }
        if (-not $content.name -or -not $content.nodes) {
            Write-Host "[FAIL] $p/$f : missing required keys (name/nodes)"
            $packPass = $false
        }
    }

    $orphans = $diskFiles | Where-Object { $manifestFiles -notcontains $_ }
    foreach ($o in $orphans) {
        Write-Host "[WARN] $p/$o : present on disk but not listed in manifest.json"
    }

    if ($packPass) {
        Write-Host "[PASS] $p : $($manifestFiles.Count) workflow file(s) OK"
    }
    else {
        $overallPass = $false
    }
}

Write-Host ""
if ($overallPass) {
    Write-Host "[OK] VALIDATION PASSED"
    exit 0
}
else {
    Write-Host "[FAIL] VALIDATION FAILED"
    exit 1
}
