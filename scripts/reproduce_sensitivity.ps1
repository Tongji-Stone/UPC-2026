param([string]$Python = 'python', [switch]$Recompute)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    $env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"
    if ($Recompute) {
        foreach ($Script in @('sensitivity_v2_compute.py','sensitivity_monte_carlo_compute.py')) {
            & $Python -B "scripts/$Script"
            if ($LASTEXITCODE -ne 0) { throw "Calculation failed: $Script" }
        }
    }
    foreach ($Script in @('build_sensitivity_assets.py')) {
        & $Python -B "scripts/$Script"
        if ($LASTEXITCODE -ne 0) { throw "Build failed: $Script" }
    }
    foreach ($Folder in @('paper','_中文版')) {
        Push-Location -LiteralPath $Folder
        try {
            1..3 | ForEach-Object {
                & xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
                if ($LASTEXITCODE -ne 0) { throw "PDF compilation failed: $Folder" }
            }
        } finally { Pop-Location }
    }
} finally { Pop-Location }
