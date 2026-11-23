$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
. ./scripts/load-env.ps1
New-Item -ItemType Directory -Force backups | Out-Null
$backupName='uyaras-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.dump'
docker compose --env-file .env.uyaras -f compose.uyaras.yaml exec -T db pg_dump -U uyaras -d uyaras -Fc -f /tmp/uyaras-backup.dump
if ($LASTEXITCODE -ne 0) { throw 'Database backup failed.' }
docker compose --env-file .env.uyaras -f compose.uyaras.yaml cp db:/tmp/uyaras-backup.dump "backups/$backupName"
if ($LASTEXITCODE -ne 0) { throw 'Could not copy backup.' }
Write-Host "Backup saved to backups/$backupName. Store encrypted off-site copies before launch."
