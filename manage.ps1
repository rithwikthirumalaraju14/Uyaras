param([Parameter(Mandatory=$true)][ValidateSet('seed','demo-stock','owner','worker','worker-once','recovery-link','test')][string]$Command, [string]$Email)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
. ./scripts/load-env.ps1
if ($Command -eq 'test') { & ./.venv/Scripts/python.exe -m pytest backend/tests -q; exit $LASTEXITCODE }
$arguments = @('-m','uyaras.manage',$Command)
if ($Email) { $arguments += @('--email',$Email) }
& ./.venv/Scripts/python.exe @arguments
exit $LASTEXITCODE
