param([ValidateSet('stitched','critical','escape','offset','six','repair','repair2','repair3','repair6','repair6b','repair6c')][string]$Candidate = 'stitched')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin\python.exe'
Push-Location $projectRoot
try {
    $source = ".cache/routing/candidate-$Candidate.kicad_pcb"
    if (!(Test-Path -LiteralPath $source)) { throw 'Evaluate the routing candidate first' }
    if ($Candidate -ne 'stitched') {
        $manifest=Get-Content "reports/pcb/$Candidate-evaluate-check.json" -Raw | ConvertFrom-Json
        if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.sha256) {throw 'Candidate changed after evaluation'}
        $drc=Get-Content $manifest.drc_report -Raw | ConvertFrom-Json
        if (@($drc.violations | Where-Object type -NotIn npth_inside_courtyard,track_dangling,via_dangling).Count) {throw 'Resolve candidate DRC before adoption'}
    }
    $backup = '.cache/routing/working-before-adoption-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.kicad_pcb'
    Copy-Item -LiteralPath 'hardware/rev-a/flight-computer.kicad_pcb' -Destination $backup
    Copy-Item -LiteralPath $source -Destination 'hardware/rev-a/flight-computer.kicad_pcb' -Force
    & $python tools/stitch-ground.py
    if ($LASTEXITCODE -ne 0) { throw 'Ground-stitch refinement failed' }
    if ($Candidate -ne 'stitched') {
        & $python tools/configure-fabrication.py --board hardware/rev-a/flight-computer.kicad_pcb --ep-report reports/pcb/ground-stitching.json
        if ($LASTEXITCODE -ne 0) { throw 'Candidate fabrication settings failed' }
    }
    & $python tools/save-placement-overrides.py
    if ($LASTEXITCODE -ne 0) { throw 'Placement preservation failed' }
    & (Join-Path $PSScriptRoot 'check-hardware.ps1')
} finally { Pop-Location }
