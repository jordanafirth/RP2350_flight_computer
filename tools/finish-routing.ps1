# Bounded, headless routing/check workflow. No GUI, uploads, Git or purchases.
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $previous='six'
    $previousCount=@((Get-Content 'reports/pcb/candidate-six-drc.json' -Raw|ConvertFrom-Json).unconnected_items).Count
    foreach ($candidate in @('repair6','repair6b','repair6c')) {
        & (Join-Path $PSScriptRoot 'complete-routing.ps1') -Source $previous -Candidate $candidate
        $report=Get-Content "reports/pcb/candidate-$candidate-drc.json" -Raw|ConvertFrom-Json
        $count=@($report.unconnected_items).Count
        $blocking=@($report.violations|Where-Object type -NotIn npth_inside_courtyard,track_dangling,via_dangling)
        if ($blocking.Count) {throw 'Resolve the raw candidate DRC violations before another completion round'}
        Write-Output "Checked $candidate : $count unconnected items"
        if ($count -eq 0 -or $count -ge $previousCount) {break}
        $previous=$candidate;$previousCount=$count
    }
} finally {Pop-Location}
