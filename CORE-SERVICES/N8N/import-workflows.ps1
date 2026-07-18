param(
    [Parameter(Mandatory = $true)][string]$Pack,
    [Parameter(Mandatory = $true)][string]$PackDir,
    [Parameter(Mandatory = $true)][string]$N8nUrl,
    [Parameter(Mandatory = $true)][string]$ApiKey,
    [switch]$Activate
)

$ErrorActionPreference = "Stop"
$headers = @{ "X-N8N-API-KEY" = $ApiKey; "Content-Type" = "application/json" }

$manifestPath = Join-Path $PackDir "manifest.json"
if (-not (Test-Path $manifestPath)) {
    Write-Host "[ERROR] No manifest.json found in $PackDir. Nothing to import."
    exit 1
}
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
if (@($manifest.workflows).Count -eq 0) {
    Write-Host "[WARN] Pack '$Pack' has no workflows recorded in manifest.json. Nothing to import."
    exit 0
}

try {
    $existing = @()
    $cursor = $null
    do {
        $uri = "$N8nUrl/api/v1/workflows?limit=100"
        if ($cursor) { $uri += "&cursor=$cursor" }
        $resp = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get
        $existing += $resp.data
        $cursor = $resp.nextCursor
    } while ($cursor)
}
catch {
    Write-Host "[ERROR] Failed to reach n8n REST API at $N8nUrl. $($_.Exception.Message)"
    exit 1
}
$byName = @{}
foreach ($e in $existing) { $byName[$e.name] = $e.id }

$imported = 0
$failed = 0

foreach ($entry in $manifest.workflows) {
    $filePath = Join-Path $PackDir $entry.file
    if (-not (Test-Path $filePath)) {
        Write-Host "[FAIL] $($entry.file) not found on disk, skipping."
        $failed++
        continue
    }
    $wf = Get-Content $filePath -Raw | ConvertFrom-Json

    $body = [ordered]@{
        name        = $wf.name
        nodes       = $wf.nodes
        connections = $wf.connections
        settings    = $wf.settings
    } | ConvertTo-Json -Depth 100

    try {
        if ($byName.ContainsKey($wf.name)) {
            $id = $byName[$wf.name]
            Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows/$id" -Headers $headers -Method Put -Body $body | Out-Null
            Write-Host "  updated: $($wf.name) (id=$id)"
        }
        else {
            $created = Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows" -Headers $headers -Method Post -Body $body
            $id = $created.id
            Write-Host "  created: $($wf.name) (id=$id)"
        }

        # Best-effort tagging: the tag API shape has changed across n8n versions,
        # so a failure here is a warning, not an import failure.
        try {
            $tags = Invoke-RestMethod -Uri "$N8nUrl/api/v1/tags" -Headers $headers -Method Get
            $tag = $tags.data | Where-Object { $_.name -eq $Pack } | Select-Object -First 1
            if (-not $tag) {
                $tag = Invoke-RestMethod -Uri "$N8nUrl/api/v1/tags" -Headers $headers -Method Post -Body (@{ name = $Pack } | ConvertTo-Json)
            }
            $tagBody = @{ tagIds = @($tag.id) } | ConvertTo-Json
            Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows/$id/tags" -Headers $headers -Method Put -Body $tagBody | Out-Null
        }
        catch {
            Write-Host "  [WARN] could not confirm/apply tag '$Pack' on $($wf.name) -- apply manually in n8n if needed."
        }

        if ($Activate) {
            try {
                Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows/$id/activate" -Headers $headers -Method Post | Out-Null
                Write-Host "  activated: $($wf.name)"
            }
            catch {
                Write-Host "  [WARN] could not activate $($wf.name): $($_.Exception.Message)"
            }
        }

        $imported++
    }
    catch {
        Write-Host "[FAIL] $($wf.name): $($_.Exception.Message)"
        $failed++
    }
}

Write-Host ""
Write-Host "[OK] Import finished for pack '$Pack': $imported imported/updated, $failed failed."
if ($failed -gt 0) { exit 1 } else { exit 0 }
