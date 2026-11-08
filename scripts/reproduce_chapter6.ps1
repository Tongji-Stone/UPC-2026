param([string]$Python='python',[switch]$Recompute)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    $env:PYTHONPATH="$ProjectRoot\src;$env:PYTHONPATH"
    foreach($Task in @('torque','wind','verify')) {
        $TaskArguments=@('-B','scripts/chapter6_compute.py',$Task)
        if($Recompute) { $TaskArguments+='--force' }
        & $Python @TaskArguments
        if($LASTEXITCODE -ne 0) { throw "Chapter 6 calculation failed: $Task" }
    }
    foreach($Script in @('chapter6_plot.py','chapter6_paper_values.py','chapter6_verify.py')) {
        & $Python -B "scripts/$Script"
        if($LASTEXITCODE -ne 0) { throw "Chapter 6 generation failed: $Script" }
    }
} finally { Pop-Location }
