param([switch]$SetupOnly,[switch]$DemoStock,[int]$Port=3000)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
$pythonExe=Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    if (Get-Command uv -ErrorAction SilentlyContinue) { uv venv --python 3.12 .venv }
    else { py -3.12 -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 environment creation failed.' }
}
if (Get-Command uv -ErrorAction SilentlyContinue) { uv pip install --python $pythonExe -r backend/requirements.txt -r requirements-dev.txt }
else { & $pythonExe -m ensurepip; & $pythonExe -m pip install -r backend/requirements.txt -r requirements-dev.txt }
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
if (-not (Test-Path -LiteralPath '.env.uyaras')) {
    $secret=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')
    $webhook=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')
    @("UYARAS_DB_PASSWORD=$secret","UYARAS_DATABASE_URL=postgresql+psycopg://uyaras:$secret@127.0.0.1:5434/uyaras",'APP_ENV=development',"PUBLIC_ORIGIN=http://localhost:$Port","MOCK_WEBHOOK_SECRET=$webhook") | Set-Content -LiteralPath '.env.uyaras' -Encoding ASCII
}
. "$PSScriptRoot/load-env.ps1"
$env:PUBLIC_ORIGIN="http://localhost:$Port"
docker compose --env-file .env.uyaras -f compose.uyaras.yaml up -d --wait
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and retry. PostgreSQL is required.' }
& $pythonExe -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed.' }
& $pythonExe -m uyaras.manage seed
if ($LASTEXITCODE -ne 0) { throw 'Catalog seed failed.' }
if ($DemoStock) { & $pythonExe -m uyaras.manage demo-stock; if ($LASTEXITCODE -ne 0) { throw 'Demo stock setup failed.' } }
if (-not (Test-Path -LiteralPath 'frontend/node_modules')) { npm.cmd ci --prefix frontend; if ($LASTEXITCODE -ne 0) { throw 'Frontend install failed.' } }
if ($SetupOnly) { Write-Host 'Setup complete. Real stock is zero unless you explicitly added demo stock.'; return }
if (Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue) { throw 'Port 8001 is already in use. Stop the earlier backend before starting.' }
New-Item -ItemType Directory -Force tmp | Out-Null
$backend=Start-Process -FilePath $pythonExe -ArgumentList @('-m','uvicorn','uyaras.main:create_app','--factory','--host','127.0.0.1','--port','8001','--no-access-log') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root 'tmp/backend.log') -RedirectStandardError (Join-Path $root 'tmp/backend-error.log')
$worker=Start-Process -FilePath $pythonExe -ArgumentList @('-m','uyaras.manage','worker') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root 'tmp/worker.log') -RedirectStandardError (Join-Path $root 'tmp/worker-error.log')
try {
    Write-Host "Open http://localhost:$Port | Staff: /admin | API docs: http://127.0.0.1:8001/docs"
    Write-Host 'Press Ctrl+C to stop the application. PostgreSQL data stays in Docker.'
    npm.cmd --prefix frontend run dev -- --hostname 127.0.0.1 --port $Port
} finally {
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue }
    if (-not $worker.HasExited) { Stop-Process -Id $worker.Id -ErrorAction SilentlyContinue }
}
