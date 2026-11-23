param([ValidateSet('complete4')][string]$Candidate='complete4')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $source=".cache/routing/candidate-$Candidate.kicad_pcb"
    $manifest=Get-Content "reports/pcb/$Candidate-evaluate-check.json" -Raw | ConvertFrom-Json
    if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.sha256){throw 'Candidate changed after evaluation'}
    $drc=Get-Content $manifest.drc_report -Raw | ConvertFrom-Json
    if(@($drc.unconnected_items).Count -or @($drc.violations | Where-Object type -ne 'npth_inside_courtyard').Count -or @($drc.violations).Count -ne 2){throw 'Resolve candidate checks before adoption'}
    foreach($notice in $drc.violations){
        if(-not ($notice.items | Where-Object description -eq 'NPTH pad of JUSB1') -or -not ($notice.items | Where-Object description -eq 'Footprint JSD1')){throw 'Unreviewed locating-hole notice'}
    }
    $backup='.cache/routing/working-before-adoption-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.kicad_pcb'
    Copy-Item hardware/rev-a/flight-computer.kicad_pcb $backup
    Copy-Item $source hardware/rev-a/flight-computer.kicad_pcb -Force
    $python=Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin\python.exe'
    & $python tools/configure-fabrication.py --board hardware/rev-a/flight-computer.kicad_pcb --ep-report reports/pcb/complete4-ground-stitching.json
    if($LASTEXITCODE -ne 0){throw 'Fabrication settings failed'}
    & $python tools/save-placement-overrides.py
    if($LASTEXITCODE -ne 0){throw 'Placement preservation failed'}
    & (Join-Path $PSScriptRoot 'finish-routing.ps1') -Stage Check
    if($LASTEXITCODE -ne 0){throw 'Adopted board verification failed'}
} finally {Pop-Location}
