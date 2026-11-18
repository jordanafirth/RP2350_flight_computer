$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$cacheRoot = Join-Path $projectRoot '.cache\freerouting'
New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
$destination = Join-Path $cacheRoot 'freerouting-2.5.0.jar'
$expected = 'f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7'
if (!(Test-Path -LiteralPath $destination)) {
    Invoke-WebRequest -Uri 'https://github.com/freerouting/freerouting/releases/download/v2.5.0/freerouting-2.5.0.jar' -OutFile $destination
}
$actual = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'Freerouting release SHA-256 mismatch.' }
Write-Output "Verified Freerouting 2.5.0: $destination"
