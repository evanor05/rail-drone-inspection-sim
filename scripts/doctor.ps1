$ErrorActionPreference = "Continue"

Write-Host "== Windows =="
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, OsArchitecture | Format-List

Write-Host "== WSL =="
wsl --status
wsl -l -v

Write-Host "== Docker =="
Get-Service | Where-Object { $_.Name -like '*docker*' -or $_.DisplayName -like '*Docker*' } | Select-Object Name, DisplayName, Status, StartType | Format-Table
docker version
docker info --format '{{json .Runtimes}}'

Write-Host "== NVIDIA =="
nvidia-smi

Write-Host "== E drive =="
Get-PSDrive -Name E | Select-Object Name, Used, Free, Root | Format-List
Test-Path 'E:\DroneRailInspection'
