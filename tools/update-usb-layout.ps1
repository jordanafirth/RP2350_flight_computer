$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin'
$python = Join-Path $bin 'python.exe'
function Run-Step([string[]]$Arguments) {
    & $python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "USB update failed: $($Arguments -join ' ')" }
}
Push-Location $projectRoot
try {
    Run-Step @('tools/build-draft-schematic.py')
    Run-Step @('tools/apply-usb-placement.py')
    Run-Step @('tools/sync-board-metadata.py')
    Run-Step @('tools/route-board.py','export','--three-signal-layers','--dsn','.cache/routing/input-usb.dsn')
    & (Join-Path $bin 'kicad-cli.exe') pcb drc --refill-zones --save-board --schematic-parity --format json --output reports/pcb/usb-adjustment-drc.json hardware/rev-a/flight-computer.kicad_pcb
    if ($LASTEXITCODE -ne 0) { throw 'USB placement DRC execution failed' }
} finally { Pop-Location }
