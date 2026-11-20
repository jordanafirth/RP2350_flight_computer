param([Parameter(Mandatory=$true)][ValidateSet('fine','stable','stitched','sensor','signal-layers','critical','escape','offset')][string]$Candidate, [switch]$OuterGround,
    [string]$BaseBoard='hardware/rev-a/flight-computer.kicad_pcb')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin'
$cli = Join-Path $bin 'kicad-cli.exe'
$python = Join-Path $bin 'python.exe'
function Run-Step([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Candidate evaluation failed: $Executable $($Arguments -join ' ')" }
}
Push-Location $projectRoot
try {
    $session = ".cache/routing/result-$Candidate.ses"
    $board = ".cache/routing/candidate-$Candidate.kicad_pcb"
    if (!(Test-Path -LiteralPath $session)) { throw "Routing session is not complete: $session" }
    Copy-Item -LiteralPath $BaseBoard -Destination $board -Force
    # KiCad CLI discovers rules by the candidate PCB's own basename/path.
    # A scratch PCB without this context would be checked against global
    # defaults rather than the project's explicit fabrication constraints.
    $stem = [IO.Path]::ChangeExtension($board,$null).TrimEnd('.')
    Copy-Item -LiteralPath 'hardware/rev-a/flight-computer.kicad_pro' -Destination "$stem.kicad_pro" -Force
    Copy-Item -LiteralPath 'hardware/rev-a/flight-computer.kicad_dru' -Destination "$stem.kicad_dru" -Force
    $libraryRoot = (Join-Path $projectRoot 'hardware/rev-a').Replace('\','/')
    $libraryTable = (Get-Content -LiteralPath 'hardware/rev-a/fp-lib-table' -Raw).Replace('${KIPRJMOD}',$libraryRoot)
    [IO.File]::WriteAllText((Join-Path $projectRoot '.cache/routing/fp-lib-table'),$libraryTable,[Text.UTF8Encoding]::new($false))
    Run-Step $python @('tools/route-board.py','import','--board',$board,'--replace-tracks','--session',$session)
    if ($OuterGround) { Run-Step $python @('tools/route-board.py','plane','--board',$board,'--outer-ground') }
    $report = "reports/pcb/candidate-$Candidate-drc.json"
    # This scratch board has no matching schematic path. Run parity separately
    # after selecting a candidate for the project, never infer it from this DRC.
    Run-Step $cli @('pcb','drc','--refill-zones','--save-board','--format','json','--output',$report,$board)
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    [pscustomobject]@{
        candidate = $Candidate
        unconnected = @($result.unconnected_items).Count
        violations = @($result.violations).Count
        types = @($result.violations | Group-Object type | Select-Object Name,Count)
    } | ConvertTo-Json -Depth 5
} finally {
    Pop-Location
}
