param([Parameter(Mandatory=$true)][string]$Backup)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
$backupPath=(Resolve-Path -LiteralPath $Backup).Path
$restoreDb='uyaras_restore_'+(Get-Date -Format 'yyyyMMddHHmmss')
docker compose --env-file .env.uyaras -f compose.uyaras.yaml cp $backupPath db:/tmp/uyaras-restore.dump
if ($LASTEXITCODE -ne 0) { throw 'Could not copy backup into container.' }
docker compose --env-file .env.uyaras -f compose.uyaras.yaml exec -T db createdb -U uyaras $restoreDb
if ($LASTEXITCODE -ne 0) { throw 'Could not create separate restore database.' }
docker compose --env-file .env.uyaras -f compose.uyaras.yaml exec -T db pg_restore -U uyaras -d $restoreDb --no-owner --exit-on-error /tmp/uyaras-restore.dump
if ($LASTEXITCODE -ne 0) { throw 'Restore verification failed.' }
docker compose --env-file .env.uyaras -f compose.uyaras.yaml exec -T db psql -U uyaras -d $restoreDb -c 'SELECT version_num FROM alembic_version; SELECT count(*) AS products FROM products; SELECT count(*) AS orders FROM orders;'
Write-Host "Restored to separate database $restoreDb. The running Uyaras database was not modified."
