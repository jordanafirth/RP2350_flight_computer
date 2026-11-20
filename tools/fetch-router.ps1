$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$cacheRoot = Join-Path $projectRoot '.cache\freerouting'
New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
$destination = Join-Path $cacheRoot 'freerouting-2.0.1.jar'
$expected = 'd7fd0f63f52e6d74b0fad6715f87ca9f0ffd7109d66b2a584638000270592ecf'
if (!(Test-Path -LiteralPath $destination)) {
    Invoke-WebRequest -Uri 'https://github.com/freerouting/freerouting/releases/download/v2.0.1/freerouting-2.0.1.jar' -OutFile $destination
}
$actual = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'Freerouting release SHA-256 mismatch.' }
Write-Output "Verified Freerouting 2.0.1: $destination"
