param([ValidateSet('Prepare','Evaluate')][string]$Action='Evaluate',
      [ValidateSet('critical','escape','offset')][string]$Candidate='critical')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$bin=Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin'
$python=Join-Path $bin 'python.exe'
$cli=Join-Path $bin 'kicad-cli.exe'
function Run-Step([string]$Executable,[string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Critical routing check failed: $Executable $($Arguments -join ' ')" }
}
Push-Location $root
try {
    if ($Action -eq 'Prepare') {
        $prepareArgs=@('tools/prepare-critical-routing.py')
        if ($Candidate -eq 'escape') {$prepareArgs+='--escape-flash'}
        if ($Candidate -eq 'offset') {$prepareArgs=@('tools/prepare-offset-routing.py')}
        Run-Step $python $prepareArgs
        $board=".cache/routing/candidate-$Candidate-placement.kicad_pcb"
        foreach ($extension in @('kicad_pro','kicad_dru')) {
            Copy-Item "hardware/rev-a/flight-computer.$extension" ".cache/routing/candidate-$Candidate-placement.$extension" -Force
        }
        $libraryRoot=(Join-Path $root 'hardware/rev-a').Replace('\','/')
        $table=(Get-Content hardware/rev-a/fp-lib-table -Raw).Replace('${KIPRJMOD}',$libraryRoot)
        [IO.File]::WriteAllText((Join-Path $root '.cache/routing/fp-lib-table'),$table,[Text.UTF8Encoding]::new($false))
        $report="reports/pcb/$Candidate-placement-drc.json"
        Run-Step $cli @('pcb','drc','--refill-zones','--save-board','--format','json','--output',$report,$board)
    } else {
        & (Join-Path $PSScriptRoot 'evaluate-routing.ps1') -Candidate $Candidate -BaseBoard ".cache/routing/candidate-$Candidate-placement.kicad_pcb"
        $board=".cache/routing/candidate-$Candidate.kicad_pcb"
        $report="reports/pcb/candidate-$Candidate-drc.json"
        $raw=Get-Content $report -Raw | ConvertFrom-Json
        if (@($raw.violations | Where-Object type -NotIn npth_inside_courtyard,track_dangling,via_dangling).Count -eq 0) {
            Run-Step $python @('tools/stitch-ground.py','--board',$board,'--report',"reports/pcb/$Candidate-ground-stitching.json")
            Run-Step $cli @('pcb','drc','--refill-zones','--save-board','--format','json','--output',$report,$board)
        }
    }
    $raw=Get-Content $report -Raw | ConvertFrom-Json
    [pscustomobject]@{board=$board;unconnected=@($raw.unconnected_items).Count;types=@($raw.violations | Group-Object type | Select-Object Name,Count)} | ConvertTo-Json -Depth 5
    Run-Step $python @('tools/export-layout.py','--board',$board,'--strict-vias')
    Run-Step $python @('tools/check-usb-return.py','--board',$board,'--report',"reports/pcb/usb-return-$Candidate-$($Action.ToLowerInvariant())-check.json")
    if ($Action -eq 'Prepare') {
        if (@($raw.violations | Where-Object type -NotIn npth_inside_courtyard,track_dangling,via_dangling).Count) { throw 'Resolve local DRC before export' }
        Run-Step $python @('tools/route-board.py','export','--board',$board,'--three-signal-layers','--dsn',".cache/routing/input-$Candidate.dsn")
    }
    $manifest=[ordered]@{board=$board;sha256=(Get-FileHash -LiteralPath $board -Algorithm SHA256).Hash.ToLowerInvariant();action=$Action;
        unconnected=@($raw.unconnected_items).Count;drc_report=$report;unexpected_via_in_pad=$false;usb_return_screen='pass'}
    [IO.File]::WriteAllText((Join-Path $root "reports/pcb/$Candidate-$($Action.ToLowerInvariant())-check.json"),($manifest|ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))
} finally { Pop-Location }
