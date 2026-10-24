$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
    else { & python -m venv .venv }
}
& $python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m ipykernel install --user --name 'baseline-whitening-test' --display-name 'Python (baseline-whitening-test)'
exit $LASTEXITCODE
