$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin'
Push-Location $projectRoot
try {
    Copy-Item -LiteralPath 'hardware/rev-a/flight-computer.kicad_pcb' -Destination '.cache/routing/before-ground-stitching.kicad_pcb' -Force
    & (Join-Path $bin 'python.exe') tools/stitch-ground.py
    if ($LASTEXITCODE -ne 0) { throw 'Ground stitching failed' }
    & (Join-Path $bin 'kicad-cli.exe') pcb drc --refill-zones --save-board --schematic-parity --format json --output reports/pcb/ground-stitching-drc.json hardware/rev-a/flight-computer.kicad_pcb
    if ($LASTEXITCODE -ne 0) { throw 'Ground-stitching DRC failed to run' }
    & (Join-Path $bin 'python.exe') tools/route-board.py export --three-signal-layers --dsn .cache/routing/input-stitched.dsn
    if ($LASTEXITCODE -ne 0) { throw 'Stitched DSN export failed' }
} finally { Pop-Location }
