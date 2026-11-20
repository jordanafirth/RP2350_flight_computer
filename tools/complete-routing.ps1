param([ValidateSet('escape','offset','six','repair','repair2','repair6','repair6b')][string]$Source='escape',
      [ValidateSet('repair','repair2','repair3','repair6','repair6b','repair6c')][string]$Candidate='repair',
      [ValidateRange(1,100)][int]$Limit=100,[switch]$ReuseProposals)
$ErrorActionPreference='Stop'
if ($Source -eq $Candidate) {throw 'Keep the source board separate from the repair candidate'}
$root=Split-Path -Parent $PSScriptRoot
$bin=Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin'
$python=Join-Path $bin 'python.exe'
$cli=Join-Path $bin 'kicad-cli.exe'
$numeric=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
function Run-Step([string]$Executable,[string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {throw "Routing completion failed: $Executable $($Arguments -join ' ')"}
}
Push-Location $root
try {
    $sourceBoard=".cache/routing/candidate-$Source.kicad_pcb"
    $board=".cache/routing/candidate-$Candidate.kicad_pcb"
    $report="reports/pcb/candidate-$Candidate-drc.json"
    $routes=".cache/routing/$Candidate-routes.json"
    Run-Step $python @('tools/export-layout.py','--board',$sourceBoard,'--strict-vias')
    $routingArgs=@('tools/repair-routing.py','--drc',"reports/pcb/candidate-$Source-drc.json",'--output',$routes,'--limit',"$Limit")
    if ($ReuseProposals) {$routingArgs+='--deduplicate-only'}
    Run-Step $numeric $routingArgs
    Run-Step $python @('tools/import-repair-routing.py','--source',$sourceBoard,'--output',$board,'--routes',$routes)
    foreach ($extension in @('kicad_pro','kicad_dru')) {
        Copy-Item "hardware/rev-a/flight-computer.$extension" ".cache/routing/candidate-$Candidate.$extension" -Force
    }
    Run-Step $cli @('pcb','drc','--refill-zones','--save-board','--format','json','--output',$report,$board)
    $raw=Get-Content $report -Raw|ConvertFrom-Json
    if (@($raw.violations|Where-Object type -NotIn npth_inside_courtyard,track_dangling,via_dangling).Count -eq 0) {
        Run-Step $python @('tools/stitch-ground.py','--board',$board,'--report',"reports/pcb/$Candidate-ground-stitching.json")
        Run-Step $cli @('pcb','drc','--refill-zones','--save-board','--format','json','--output',$report,$board)
    }
    $raw=Get-Content $report -Raw|ConvertFrom-Json
    [pscustomobject]@{board=$board;unconnected=@($raw.unconnected_items).Count;types=@($raw.violations|Group-Object type|Select-Object Name,Count)}|ConvertTo-Json -Depth 5
    Run-Step $python @('tools/check-pcb-connectivity.py','--board',$board,'--report',"reports/pcb/$Candidate-pad-net-check.json")
    Run-Step $python @('tools/export-layout.py','--board',$board,'--strict-vias')
    Run-Step $python @('tools/check-usb-return.py','--board',$board,'--report',"reports/pcb/usb-return-$Candidate-evaluate-check.json")
    $manifest=[ordered]@{board=$board;sha256=(Get-FileHash -LiteralPath $board -Algorithm SHA256).Hash.ToLowerInvariant();action='Evaluate';
        unconnected=@($raw.unconnected_items).Count;drc_report=$report;unexpected_via_in_pad=$false;usb_return_screen='pass'}
    [IO.File]::WriteAllText((Join-Path $root "reports/pcb/$Candidate-evaluate-check.json"),($manifest|ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))
} finally {Pop-Location}
