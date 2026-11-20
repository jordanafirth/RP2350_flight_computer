param([ValidateSet('stitched')][string]$Candidate = 'stitched')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin\python.exe'
Push-Location $projectRoot
try {
    $source = ".cache/routing/candidate-$Candidate.kicad_pcb"
    if (!(Test-Path -LiteralPath $source)) { throw 'Evaluate the routing candidate first' }
    $backup = '.cache/routing/working-before-adoption-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.kicad_pcb'
    Copy-Item -LiteralPath 'hardware/rev-a/flight-computer.kicad_pcb' -Destination $backup
    Copy-Item -LiteralPath $source -Destination 'hardware/rev-a/flight-computer.kicad_pcb' -Force
    & $python tools/stitch-ground.py
    if ($LASTEXITCODE -ne 0) { throw 'Ground-stitch refinement failed' }
    & (Join-Path $PSScriptRoot 'check-hardware.ps1')
} finally { Pop-Location }
