param(
    [Parameter(Mandatory = $true)][string]$Pack,
    [Parameter(Mandatory = $true)][string]$PackDir,
    [Parameter(Mandatory = $true)][string]$N8nUrl,
    [Parameter(Mandatory = $true)][string]$ApiKey
)

$ErrorActionPreference = "Stop"
$headers = @{ "X-N8N-API-KEY" = $ApiKey }

function Get-SafeFileName([string]$name) {
    $invalid = [System.IO.Path]::GetInvalidFileNameChars() -join ''
    $pattern = "[{0}]" -f [System.Text.RegularExpressions.Regex]::Escape($invalid)
    return ($name -replace $pattern, "_")
}

try {
    $workflows = @()
    $cursor = $null
    do {
        $uri = "$N8nUrl/api/v1/workflows?tags=$Pack&limit=100"
        if ($cursor) { $uri += "&cursor=$cursor" }
        $resp = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get
        $workflows += $resp.data
        $cursor = $resp.nextCursor
    } while ($cursor)
}
catch {
    Write-Host "[ERROR] Failed to reach n8n REST API at $N8nUrl. $($_.Exception.Message)"
    exit 1
}

Write-Host "Found $($workflows.Count) workflow(s) tagged '$Pack'."

# Clear stale exports so renamed/deleted workflows don't leave orphan files behind.
Get-ChildItem -Path $PackDir -Filter *.json -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne "manifest.json" } | Remove-Item -Force

$manifestEntries = @()
foreach ($wf in $workflows) {
    $fileName = "$(Get-SafeFileName $wf.name)_$($wf.id).json"
    $filePath = Join-Path $PackDir $fileName
    $wf | ConvertTo-Json -Depth 100 | Set-Content -Path $filePath -Encoding UTF8

    $manifestEntries += [ordered]@{
        id        = $wf.id
        name      = $wf.name
        file      = $fileName
        active    = $wf.active
        updatedAt = $wf.updatedAt
        tags      = @($wf.tags | ForEach-Object { $_.name })
    }
    Write-Host "  exported: $($wf.name) -> $fileName"
}

$now = (Get-Date).ToString("o")
$packManifest = [ordered]@{
    pack            = $Pack
    description     = "Workflows tagged `"$Pack`" in n8n."
    n8nTag          = $Pack
    manifestVersion = 1
    lastExportAt    = $now
    source          = "$N8nUrl/api/v1/workflows"
    workflows       = $manifestEntries
}
$packManifest | ConvertTo-Json -Depth 100 | Set-Content -Path (Join-Path $PackDir "manifest.json") -Encoding UTF8

$rootManifestPath = Join-Path (Split-Path $PackDir -Parent) "manifest.json"
$rootManifest = Get-Content $rootManifestPath -Raw | ConvertFrom-Json
$rootManifest.packs.$Pack.workflowCount = $manifestEntries.Count
$rootManifest.packs.$Pack.lastExportAt = $now
$rootManifest | ConvertTo-Json -Depth 100 | Set-Content -Path $rootManifestPath -Encoding UTF8

Write-Host "[OK] Pack '$Pack' exported: $($manifestEntries.Count) workflow(s)."
