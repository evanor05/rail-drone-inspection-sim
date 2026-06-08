param(
    [string]$Url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Models = Join-Path $Root "data\models"
New-Item -ItemType Directory -Force -Path $Models | Out-Null
$Out = Join-Path $Models "yolov8n.pt"
Write-Host "[DRI] Downloading YOLO weights to $Out"
Invoke-WebRequest -Uri $Url -OutFile $Out
Write-Host "[DRI] Download complete. For rail-specific training place weights at data\models\rail_defects.pt"
