param([string]$Python = 'python', [switch]$RefreshFiguresOnly, [switch]$Recompute)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    $env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"
    if (-not $RefreshFiguresOnly) {
        foreach ($Task in @('prepare','forward','inverse','other','collect')) {
            $TaskArguments=@('-B','scripts/four_model_compute.py',$Task)
            if ($Task -eq 'inverse' -and $Recompute) { $TaskArguments+='--force' }
            & $Python @TaskArguments
            if ($LASTEXITCODE -ne 0) { throw "Calculation failed: $Task" }
        }
    }
    foreach ($Script in @('four_model_verify.py','chapter4_compute.py','four_model_plot.py','four_model_paper_values.py','verify_chapter4.py')) {
        & $Python -B "scripts/$Script"
        if ($LASTEXITCODE -ne 0) { throw "Report update failed: $Script" }
    }
    & $Python -B -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Model tests failed' }
    & "$PSScriptRoot/reproduce_sensitivity.ps1" -Python $Python -Recompute:$Recompute
} finally { Pop-Location }
