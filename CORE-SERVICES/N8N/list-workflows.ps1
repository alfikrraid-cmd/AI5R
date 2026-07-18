param(
    [string]$Pack,
    [Parameter(Mandatory = $true)][string]$WorkflowsDir,
    [string]$N8nUrl,
    [string]$ApiKey
)

$ErrorActionPreference = "Stop"
$packs = @("COMMON", "LTSA", "AUDITOR", "SCHOOL", "UMKM")
if ($Pack) { $packs = @($Pack) }

foreach ($p in $packs) {
    $manifestPath = Join-Path (Join-Path $WorkflowsDir $p) "manifest.json"
    if (-not (Test-Path $manifestPath)) {
        Write-Host "$p : manifest not found (never exported)"
        continue
    }
    $m = Get-Content $manifestPath -Raw | ConvertFrom-Json
    $count = @($m.workflows).Count
    $last = if ($m.lastExportAt) { $m.lastExportAt } else { "never" }
    Write-Host ""
    Write-Host "=== $p ($count workflow(s), last export: $last) ==="
    foreach ($wf in $m.workflows) {
        $activeMark = if ($wf.active) { "[active]" } else { "[inactive]" }
        Write-Host ("  {0,-40} {1} {2}" -f $wf.name, $activeMark, $wf.id)
    }
}

if ($ApiKey) {
    try {
        $headers = @{ "X-N8N-API-KEY" = $ApiKey }
        Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows?limit=1" -Headers $headers -Method Get | Out-Null
        Write-Host ""
        Write-Host "n8n API reachable at $N8nUrl (live)."
    }
    catch {
        Write-Host ""
        Write-Host "[WARN] n8n API not reachable at $N8nUrl -- showing local manifest data only."
    }
}
else {
    Write-Host ""
    Write-Host "[INFO] N8N_API_KEY not set -- showing local manifest data only (no live check)."
}
