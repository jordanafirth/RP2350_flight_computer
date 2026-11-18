$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$referenceRoot = Join-Path $projectRoot 'references'
$manifestPath = Join-Path $referenceRoot 'manifest.json'
$headers = @{ 'User-Agent' = 'FlightComputer-ReferenceAudit'; 'Accept' = 'application/vnd.github+json' }
$repoNames = @(
    'Adafruit-Feather-RP2040-Adalogger-PCB',
    'Adafruit-Feather-RP2350-PCB',
    'Adafruit-BNO08x-PCB',
    'Adafruit-BMP280-Breakout-PCB'
)
$previous = if (Test-Path -LiteralPath $manifestPath) { Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json } else { @() }
$records = @()
foreach ($repoName in $repoNames) {
    $fullName = "adafruit/$repoName"
    $oldRecord = $previous | Where-Object { $_.repository -eq $fullName } | Select-Object -First 1
    if ($oldRecord) {
        $revision = $oldRecord.commit
    } else {
        $repo = Invoke-RestMethod -Uri "https://api.github.com/repos/$fullName" -Headers $headers
        $commit = Invoke-RestMethod -Uri "https://api.github.com/repos/$fullName/commits/$($repo.default_branch)" -Headers $headers
        $revision = $commit.sha
    }
    if ($revision -notmatch '^[0-9a-f]{40}$') { throw "Invalid revision for $fullName" }
    $tree = Invoke-RestMethod -Uri "https://api.github.com/repos/$fullName/git/trees/${revision}?recursive=1" -Headers $headers
    if ($tree.truncated) { throw "Incomplete source tree for $fullName" }
    $selected = @($tree.tree | Where-Object {
        $_.type -eq 'blob' -and ($_.path -match '\.(brd|sch)$' -or $_.path -match '(^|/)(license[^/]*|readme[^/]*)$')
    })
    $files = @()
    foreach ($entry in $selected) {
        $relative = $entry.path
        if ($relative -match '(^/|\\|(^|/)\.\.(/|$)|:)') { throw "Unsafe upstream path: $relative" }
        $destination = Join-Path (Join-Path $referenceRoot $repoName) $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        $escapedPath = (($relative -split '/') | ForEach-Object { [Uri]::EscapeDataString($_) }) -join '/'
        $url = "https://raw.githubusercontent.com/$fullName/$revision/$escapedPath"
        Invoke-WebRequest -Uri $url -Headers $headers -OutFile $destination
        $files += [ordered]@{ path = $relative; source = $url; sha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() }
    }
    $records += [ordered]@{ repository = $fullName; commit = $revision; retrieved_utc = [DateTime]::UtcNow.ToString('o'); files = $files }
    $records | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
    Write-Output "$fullName @ $revision : $($files.Count) reference files"
}
