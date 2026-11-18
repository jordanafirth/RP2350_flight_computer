param(
    [string]$KiCadCli,
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (!$KiCadCli) {
    $KiCadCli = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin\kicad-cli.exe'
    if (!(Test-Path -LiteralPath $KiCadCli)) {
        $KiCadCli = (Get-Command kicad-cli -ErrorAction Stop).Source
    }
}
if (!$Python) { $Python = Join-Path (Split-Path -Parent $KiCadCli) 'python.exe' }
function Run-Step([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Executable $($Arguments -join ' ')" }
}
Push-Location $projectRoot
try {
    & (Join-Path $PSScriptRoot 'audit-eagle.ps1')
    New-Item -ItemType Directory -Force -Path 'hardware/imports/boards','reports/schematic','hardware/rev-a/exports' | Out-Null
    $boards = @(
        @{ name='rp2350'; source='references/Adafruit-Feather-RP2350-PCB/Adafruit Feather RP2350.brd' },
        @{ name='adalogger'; source='references/Adafruit-Feather-RP2040-Adalogger-PCB/Adafruit Feather RP2040 Adalogger.brd' },
        @{ name='bno085'; source='references/Adafruit-BNO08x-PCB/Adafruit_BNO08x.brd' },
        @{ name='bmp581'; source='references/Adafruit-BMP5xx-Temperature-and-Pressure-Sensor-PCB/Adafruit BMP581 Temperature and Pressure Sensor rev B.brd' }
    )
    foreach ($board in $boards) {
        $copyRoot = Join-Path 'hardware/imports/board-sources' $board.name
        New-Item -ItemType Directory -Force -Path $copyRoot | Out-Null
        $copyPath = Join-Path $copyRoot 'reference.brd'
        Copy-Item -LiteralPath $board.source -Destination $copyPath -Force
        # Eagle import can emit .kicad_dru beside its INPUT: work on copies.
        Run-Step $KiCadCli @('pcb','import','--format','eagle','--output',"hardware/imports/boards/$($board.name).kicad_pcb",'--report-format','json','--report-file',"reports/schematic/$($board.name)-board-import.json",$copyPath)
    }
    Run-Step $Python @('tools/build-draft-schematic.py')
    Run-Step $Python @('tools/extract-footprints.py')
    Run-Step $Python @('tools/check-footprints.py')
    Run-Step $KiCadCli @('sch','export','netlist','--format','kicadxml','--output','reports/schematic/flight-computer.net.xml','hardware/rev-a/flight-computer.kicad_sch')
    Run-Step $Python @('tools/check-connectivity.py')
    Run-Step $KiCadCli @('sch','erc','--exit-code-violations','--format','json','--output','reports/schematic/erc.json','hardware/rev-a/flight-computer.kicad_sch')
    Run-Step $KiCadCli @('sch','export','svg','--output','hardware/rev-a/exports/','hardware/rev-a/flight-computer.kicad_sch')
    Write-Output 'Hardware draft rebuilt and checks passed. No PCB layout or manufacturing release was generated.'
} finally {
    Pop-Location
}
