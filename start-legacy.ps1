param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv venv --python 3.12 .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
    } else {
        py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 or uv, then run this script again.' }
    }
}
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv pip install --python $pythonExe -r requirements.txt
} else {
    & $pythonExe -m pip install -r requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $pythonExe -m app.manage seed
if ($LASTEXITCODE -ne 0) { throw 'Sample setup failed.' }
Write-Host "Open http://127.0.0.1:$Port"
& $pythonExe -m uvicorn app.commerce:app --host 127.0.0.1 --port $Port --no-access-log
