param([switch]$SetupOnly,[switch]$DemoStock,[int]$Port=3000)
& "$PSScriptRoot/scripts/start-uyaras.ps1" -SetupOnly:$SetupOnly -DemoStock:$DemoStock -Port $Port
