$ErrorActionPreference = "Stop"

$service = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
if ($service -and $service.Status -ne "Running") {
    Write-Host "[DRI] Starting Docker Desktop service"
    Start-Service -Name "com.docker.service"
}

$desktop = Join-Path $Env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
if (Test-Path $desktop) {
    Write-Host "[DRI] Starting Docker Desktop UI/backend"
    Start-Process -FilePath $desktop -WindowStyle Hidden
} else {
    Write-Warning "Docker Desktop executable not found at $desktop"
}

Write-Host "[DRI] Waiting for Docker daemon..."
for ($i = 0; $i -lt 60; $i++) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[DRI] Docker daemon is ready"
        exit 0
    }
    Start-Sleep -Seconds 2
}
throw "Docker daemon did not become ready within 120 seconds."
