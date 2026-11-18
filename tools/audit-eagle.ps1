$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$referenceRoot = Join-Path $projectRoot 'references'
$reportRoot = Join-Path $projectRoot 'reports'
New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null
$manifestPath = Join-Path $referenceRoot 'manifest.json'
if (!(Test-Path -LiteralPath $manifestPath)) { throw 'Acquire references first.' }
$manifest = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
$results = @()
$invariant = [Globalization.CultureInfo]::InvariantCulture
function Read-Number([string]$value) { [double]::Parse($value, $invariant) }
foreach ($reference in $manifest) {
    $repoName = ($reference.repository -split '/')[-1]
    foreach ($source in @($reference.files)) {
        $localPath = Join-Path (Join-Path $referenceRoot $repoName) $source.path
        if ((Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $source.sha256) {
            throw "Source hash mismatch: $localPath"
        }
        if ($source.path -notmatch '\.(brd|sch)$') { continue }
        $settings = [Xml.XmlReaderSettings]::new()
        $settings.DtdProcessing = [Xml.DtdProcessing]::Ignore
        $settings.XmlResolver = $null
        $reader = [Xml.XmlReader]::Create($localPath, $settings)
        $xml = [Xml.XmlDocument]::new()
        try { $xml.Load($reader) } finally { $reader.Dispose() }
        $board = $xml.SelectSingleNode('/eagle/drawing/board')
        $schematic = $xml.SelectSingleNode('/eagle/drawing/schematic')
        if (!$board -and !$schematic) { throw "Not an Eagle board/schematic: $localPath" }
        if ($schematic) {
            $results += [ordered]@{
                repository = $reference.repository; commit = $reference.commit; path = $source.path; kind = 'schematic'
                parts = @($schematic.SelectNodes('parts/part') | ForEach-Object {
                    [ordered]@{ name = $_.GetAttribute('name'); value = $_.GetAttribute('value'); library = $_.GetAttribute('library'); deviceset = $_.GetAttribute('deviceset'); device = $_.GetAttribute('device') }
                })
                nets = @($schematic.SelectNodes('sheets/sheet/nets/net') | ForEach-Object {
                    [ordered]@{ name = $_.GetAttribute('name'); pins = @($_.SelectNodes('segment/pinref') | ForEach-Object { "$($_.GetAttribute('part')).$($_.GetAttribute('gate')).$($_.GetAttribute('pin'))" }) }
                })
            }
            continue
        }
        $outline = @($board.SelectNodes('plain/wire[@layer="20"]'))
        $xs = @($outline | ForEach-Object { Read-Number $_.GetAttribute('x1'); Read-Number $_.GetAttribute('x2') })
        $ys = @($outline | ForEach-Object { Read-Number $_.GetAttribute('y1'); Read-Number $_.GetAttribute('y2') })
        $elements = @($board.SelectNodes('elements/element') | ForEach-Object {
            $element = $_
            $library = @($board.SelectNodes('libraries/library') | Where-Object { $_.GetAttribute('name') -eq $element.GetAttribute('library') })[0]
            $package = @($library.SelectNodes('packages/package') | Where-Object { $_.GetAttribute('name') -eq $element.GetAttribute('package') })[0]
            [ordered]@{
                name = $_.GetAttribute('name'); value = $_.GetAttribute('value'); package = $_.GetAttribute('package'); library = $_.GetAttribute('library')
                x_mm = Read-Number $_.GetAttribute('x'); y_mm = Read-Number $_.GetAttribute('y'); rotation = $_.GetAttribute('rot')
                face = if ($_.GetAttribute('rot') -match 'M') { 'bottom' } else { 'top' }
                smd_pad_count = $package.SelectNodes('smd').Count
                through_hole_pad_count = $package.SelectNodes('pad').Count
            }
        })
        $signals = @($board.SelectNodes('signals/signal') | ForEach-Object {
            [ordered]@{ name = $_.GetAttribute('name'); pads = @($_.SelectNodes('contactref') | ForEach-Object { "$($_.GetAttribute('element')).$($_.GetAttribute('pad'))" }) }
        })
        $results += [ordered]@{
            repository = $reference.repository; commit = $reference.commit; path = $source.path; kind = 'board'
            outline_endpoint_bounds_mm = if ($outline.Count) {
                [ordered]@{ min_x = ($xs | Measure-Object -Minimum).Minimum; max_x = ($xs | Measure-Object -Maximum).Maximum; min_y = ($ys | Measure-Object -Minimum).Minimum; max_y = ($ys | Measure-Object -Maximum).Maximum; note = 'Bounds of layer-20 wire endpoints only; curved-outline extrema and manufacturing tolerances require CAD review.' }
            } else { $null }
            top_elements = @($elements | Where-Object { $_.face -eq 'top' }).Count
            bottom_elements = @($elements | Where-Object { $_.face -eq 'bottom' }).Count
            bottom_elements_with_contacts = @($elements | Where-Object { $_.face -eq 'bottom' -and ($_.smd_pad_count + $_.through_hole_pad_count) -gt 0 }).Count
            elements = $elements; signals = $signals
            routing_layers = @($board.SelectNodes('signals/signal/wire') | ForEach-Object { $_.GetAttribute('layer') } | Sort-Object -Unique)
            mounting_holes = @($board.SelectNodes('plain/hole') | ForEach-Object {
                [ordered]@{ x_mm = Read-Number $_.GetAttribute('x'); y_mm = Read-Number $_.GetAttribute('y'); drill_mm = Read-Number $_.GetAttribute('drill') }
            })
        }
    }
}
$results | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $reportRoot 'reference-audit.json') -Encoding utf8
$lines = [Collections.Generic.List[string]]::new()
$lines.Add('# Automated Eagle reference inventory')
$lines.Add('')
$lines.Add('Generated by tools/audit-eagle.ps1. All downloaded-file hashes checked against references/manifest.json. This is a source inventory, not electrical-rule checking or a custom-board validation.')
$lines.Add('')
foreach ($result in $results | Where-Object { $_.kind -eq 'board' }) {
    $lines.Add("## $($result.repository) / $($result.path)")
    $lines.Add('')
    $lines.Add("Revision: $($result.commit)")
    $lines.Add('')
    $lines.Add("Top elements: $($result.top_elements); bottom elements: $($result.bottom_elements). Trace layers used: $($result.routing_layers -join ', ').")
    $lines.Add("Bottom elements with copper contacts: $($result.bottom_elements_with_contacts). Element totals include graphics, labels, holes and test pads; they are not populated-component counts.")
    if ($result.outline_endpoint_bounds_mm) {
        $b = $result.outline_endpoint_bounds_mm
        $width = [Math]::Round(($b.max_x - $b.min_x), 4)
        $height = [Math]::Round(($b.max_y - $b.min_y), 4)
        $lines.Add("Layer-20 wire endpoint span: $width x $height mm. Curves/tolerances need CAD review.")
    }
    $lines.Add('')
    $lines.Add('| Reference | Value | Package | Face | X mm | Y mm |')
    $lines.Add('| --- | --- | --- | --- | --- | --- |')
    foreach ($part in $result.elements) {
        $value = $part.value -replace '\|','/'
        $package = $part.package -replace '\|','/'
        $lines.Add("| $($part.name) | $value | $package | $($part.face) | $($part.x_mm) | $($part.y_mm) |")
    }
    $lines.Add('')
}
[IO.File]::WriteAllText((Join-Path $reportRoot 'reference-audit.md'), (($lines -join "`n") + "`n"), [Text.UTF8Encoding]::new($false))
Write-Output "Verified source hashes and parsed $($results.Count) CAD files. Reports written to reports/reference-audit.json and .md."
