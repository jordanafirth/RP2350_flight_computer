# Check the completed routed board; never regenerate placement or copper here.
param([ValidateSet('All','Check')][string]$Stage='Check')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$bin=Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin'
Push-Location $root
try {
    & (Join-Path $PSScriptRoot 'check-hardware.ps1')
    if($LASTEXITCODE -ne 0){throw 'Hardware checks failed'}
    $drc=Get-Content 'reports/pcb/current-drc.json' -Raw | ConvertFrom-Json
    if(@($drc.unconnected_items).Count){throw 'Disconnected nets remain'}
    $notices=@($drc.violations | Where-Object type -eq 'npth_inside_courtyard')
    if(@($drc.violations | Where-Object type -ne 'npth_inside_courtyard').Count -or $notices.Count -ne 2){throw 'Unexpected board-rule result'}
    foreach($notice in $notices){
        if(-not ($notice.items | Where-Object description -eq 'NPTH pad of JUSB1') -or -not ($notice.items | Where-Object description -eq 'Footprint JSD1')){throw 'Unreviewed locating-hole notice'}
    }
    & "$bin\python.exe" tools/export-layout.py --strict-vias --require-ep-vias
    if($LASTEXITCODE -ne 0){throw 'Via screening failed'}
    & "$bin\python.exe" tools/check-usb-return.py --board hardware/rev-a/flight-computer.kicad_pcb
    if($LASTEXITCODE -ne 0){throw 'USB ground-reference screen failed'}
} finally {Pop-Location}
