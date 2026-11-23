$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env.uyaras'
if (-not (Test-Path -LiteralPath $envFile)) { throw 'Run start.ps1 -SetupOnly first.' }
Get-Content -LiteralPath $envFile | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') }
}
$env:PYTHONPATH = Join-Path (Split-Path $PSScriptRoot -Parent) 'backend'
$env:NEXT_TELEMETRY_DISABLED = '1'
