param([string]$Python = 'python', [switch]$RefreshFiguresOnly)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    $env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"
    if (-not $RefreshFiguresOnly) {
        foreach ($Task in @('prepare','forward','inverse','other','collect')) {
            & $Python scripts/four_model_compute.py $Task
            if ($LASTEXITCODE -ne 0) { throw "Calculation failed: $Task" }
        }
    }
    foreach ($Script in @('four_model_plot.py','four_model_paper_values.py','four_model_verify.py')) {
        & $Python "scripts/$Script"
        if ($LASTEXITCODE -ne 0) { throw "Script failed: $Script" }
    }
    Push-Location -LiteralPath paper/assets
    try {
        & xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error workflow_vector.tex
        if ($LASTEXITCODE -ne 0) { throw 'Workflow compilation failed' }
    } finally { Pop-Location }
    foreach ($Edition in @('paper','_中文版')) {
        if (Test-Path -LiteralPath $Edition) {
            Push-Location -LiteralPath $Edition
            try {
                1..3 | ForEach-Object {
                    & xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
                    if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX failed' }
                }
            } finally { Pop-Location }
        }
    }
    & $Python scripts/four_model_pdf_check.py
    if ($LASTEXITCODE -ne 0) { throw 'PDF verification failed' }
    if (Test-Path -LiteralPath '_中文版') {
        & $Python scripts/verify_bilingual_reports.py
        if ($LASTEXITCODE -ne 0) { throw 'Bilingual verification failed' }
    }
} finally { Pop-Location }
