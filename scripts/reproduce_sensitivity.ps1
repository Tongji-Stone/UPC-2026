param([string]$Python = 'python', [switch]$Recompute)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    $env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"
    if ($Recompute) {
        foreach ($Script in @('sensitivity_reference_compute.py','sensitivity_v2_compute.py','sensitivity_v2_check.py','sensitivity_monte_carlo_compute.py','review_fig13_compute.py','review_fig13_plot.py')) {
            & $Python -B "scripts/$Script"
            if ($LASTEXITCODE -ne 0) { throw "Calculation failed: $Script" }
        }
    }
    & $Python -B scripts/build_sensitivity_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Sensitivity figures and tables failed' }
    foreach ($Folder in @('paper','_中文版')) {
        Push-Location -LiteralPath $Folder
        try {
            1..3 | ForEach-Object {
                & xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
                if ($LASTEXITCODE -ne 0) { throw "PDF compilation failed: $Folder" }
            }
        } finally { Pop-Location }
    }
    foreach ($Script in @('four_model_pdf_check.py','verify_bilingual_reports.py','verify_sensitivity_integration.py')) {
        & $Python -B "scripts/$Script"
        if ($LASTEXITCODE -ne 0) { throw "Paper verification failed: $Script" }
    }
} finally { Pop-Location }
