param(
    [string]$InputDsn = '.cache/routing/input-fine.dsn',
    [string]$OutputSes = '.cache/routing/result-fine.ses',
    [ValidateRange(1,30)][int]$Passes = 5
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$jdk = 'C:\Program Files\JetBrains\CLion 2026.3.0.1\jbr\bin'
$jar = Join-Path $projectRoot '.cache/freerouting/freerouting-2.0.1.jar'
$expected = 'd7fd0f63f52e6d74b0fad6715f87ca9f0ffd7109d66b2a584638000270592ecf'
if ((Get-FileHash -LiteralPath $jar -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw 'Freerouting 2.0.1 SHA-256 mismatch'
}
$cache = Join-Path $projectRoot '.cache/router-runner'
New-Item -ItemType Directory -Force -Path $cache | Out-Null
& (Join-Path $jdk 'javac.exe') '-cp' $jar '-d' $cache (Join-Path $PSScriptRoot 'RouteBoard.java')
if ($LASTEXITCODE -ne 0) { throw 'Routing runner compilation failed' }
Push-Location $projectRoot
try {
    & (Join-Path $jdk 'java.exe') '-Djava.awt.headless=true' '-Xmx2g' '-cp' "$jar;$cache" 'RouteBoard' $InputDsn $OutputSes "$Passes"
    if ($LASTEXITCODE -ne 0) { throw 'Routing failed' }
} finally { Pop-Location }
