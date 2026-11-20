$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin'
$python = Join-Path $bin 'python.exe'
Push-Location $projectRoot
try {
    & $python tools/prepare-sensor-routing.py
    if ($LASTEXITCODE -ne 0) { throw 'Sensor preparation failed' }
    $stem = '.cache/routing/candidate-sensor-placement'
    Copy-Item -LiteralPath 'hardware/rev-a/flight-computer.kicad_pro' -Destination "$stem.kicad_pro" -Force
    Copy-Item -LiteralPath 'hardware/rev-a/flight-computer.kicad_dru' -Destination "$stem.kicad_dru" -Force
    $libraryRoot = (Join-Path $projectRoot 'hardware/rev-a').Replace('\','/')
    $table = (Get-Content hardware/rev-a/fp-lib-table -Raw).Replace('${KIPRJMOD}',$libraryRoot)
    [IO.File]::WriteAllText((Join-Path $projectRoot '.cache/routing/fp-lib-table'),$table,[Text.UTF8Encoding]::new($false))
    & (Join-Path $bin 'kicad-cli.exe') pcb drc --refill-zones --save-board --format json --output reports/pcb/sensor-placement-drc.json "$stem.kicad_pcb"
    if ($LASTEXITCODE -ne 0) { throw 'Sensor candidate DRC could not run' }
    $result = Get-Content reports/pcb/sensor-placement-drc.json -Raw | ConvertFrom-Json
    $result.violations | Group-Object type | Select-Object Name,Count | ConvertTo-Json
    $blocking = @($result.violations | Where-Object type -NotIn npth_inside_courtyard,track_dangling,via_dangling)
    if ($blocking.Count) { throw "Resolve $($blocking.Count) physical/routing violations before exporting the sensor candidate" }
    & $python tools/route-board.py export --board "$stem.kicad_pcb" --three-signal-layers --dsn .cache/routing/input-sensor.dsn
    if ($LASTEXITCODE -ne 0) { throw 'Sensor candidate DSN export failed' }
} finally { Pop-Location }
