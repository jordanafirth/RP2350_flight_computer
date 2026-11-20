param([string]$PcbReport = 'reports/pcb/current-drc.json', [switch]$PreviewOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin'
$cli = Join-Path $bin 'kicad-cli.exe'
$python = Join-Path $bin 'python.exe'
function Run-Step([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Check failed ($LASTEXITCODE): $Executable $($Arguments -join ' ')" }
}
Push-Location $projectRoot
try {
    if (!$PreviewOnly) {
    Run-Step $python @('tools/check-footprints.py')
    Run-Step $cli @('sch','export','netlist','--format','kicadxml','--output','reports/schematic/flight-computer.net.xml','hardware/rev-a/flight-computer.kicad_sch')
    Run-Step $python @('tools/check-connectivity.py')
    Run-Step $cli @('sch','erc','--exit-code-violations','--format','json','--output','reports/schematic/erc.json','hardware/rev-a/flight-computer.kicad_sch')
    Run-Step $cli @('sch','export','svg','--output','hardware/rev-a/exports/','hardware/rev-a/flight-computer.kicad_sch')
    # Preserve raw violations. A generated report is not a release approval.
    Run-Step $cli @('pcb','drc','--refill-zones','--save-board','--schematic-parity','--format','json','--output',$PcbReport,'hardware/rev-a/flight-computer.kicad_pcb')
    }
    Run-Step $python @('tools/route-board.py','pads','--quiet')
    Run-Step $cli @('pcb','export','svg','--mode-single','--layers','F.Cu,F.Fab,Edge.Cuts','--output','.cache/current-top.svg','hardware/rev-a/flight-computer.kicad_pcb')
    Run-Step $cli @('pcb','export','svg','--mode-single','--layers','B.Cu,B.Fab,Edge.Cuts','--output','.cache/current-bottom.svg','hardware/rev-a/flight-computer.kicad_pcb')
    $inkscape = 'C:\Program Files\Inkscape\bin\inkscape.com'
    if (Test-Path -LiteralPath $inkscape) {
        foreach ($face in @('top','bottom')) {
            # Fixed engineering viewport includes PCB, connector overhang and
            # small margins; omit the large surrounding A4 worksheet in PNGs.
            Run-Step $inkscape @(".cache/current-$face.svg",'--export-area=370.394:370.394:597.165:472.441','--export-width=2200',"--export-filename=.cache/current-$face.png")
            Copy-Item -LiteralPath ".cache/current-$face.svg" -Destination "hardware/rev-a/exports/placement-$face.svg" -Force
            Copy-Item -LiteralPath ".cache/current-$face.png" -Destination "hardware/rev-a/exports/placement-$face.png" -Force
        }
        foreach ($sheet in @('Power','Processor','Sensors','Interfaces')) {
            $source = "hardware/rev-a/exports/flight-computer-$sheet.svg"
            $preview = 'hardware/rev-a/exports/' + $sheet.ToLowerInvariant() + '-preview.png'
            Run-Step $inkscape @($source,'--export-area-page','--export-width=2200',"--export-filename=$preview")
        }
    }
    if (!$PreviewOnly) { Write-Output 'Schematic checks passed; inspect the raw PCB DRC report for unresolved layout work.' }
} finally {
    Pop-Location
}
