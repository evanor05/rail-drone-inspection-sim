param(
    [int]$DashboardPort = 8080,
    [string]$LogRoot = ".\data\exports",
    [switch]$WithDockerCompose
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Step {
    param(
        [string]$Name,
        [string]$LogName,
        [scriptblock]$Block
    )

    Write-Host "== $Name =="
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $logPath = Join-Path $LogDir $LogName
    try {
        $output = (& $Block) 2>&1 | Out-String
        Set-Content -LiteralPath $logPath -Value $output -Encoding UTF8
        Write-Host "[PASS] $Name"
        return [PSCustomObject]@{
            name = $Name
            status = "PASS"
            log = $logPath
        }
    } catch {
        $message = $_.Exception.Message
        $output = "$message`n$($_ | Out-String)"
        Set-Content -LiteralPath $logPath -Value $output -Encoding UTF8
        Write-Host "[FAIL] $Name"
        Write-Host $message
        return [PSCustomObject]@{
            name = $Name
            status = "FAIL"
            log = $logPath
            error = $message
        }
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([System.IO.Path]::IsPathRooted($LogRoot)) {
    $logBase = $LogRoot
} else {
    $logBase = Join-Path $Root $LogRoot
}
$LogDir = Join-Path $logBase "local-verify-$timestamp"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host "== DroneRailInspection local verification =="
Write-Host "Log directory: $LogDir"
Write-Host ""

$results = @()
$results += Invoke-Step "Static project validation" "01_static_check.log" { python .\scripts\static_check.py }
$reportSmokeRoot = Join-Path $LogDir "report_smoke_data"
$results += Invoke-Step "Chinese report smoke" "02_report_smoke.log" { python .\scripts\report_smoke.py --output-root $reportSmokeRoot }
$results += Invoke-Step "YOLO dataset structure check" "03_dataset_check.log" { python .\scripts\dataset_check.py }
$rlSmokeOutput = Join-Path $LogDir "rl_policy_eval_smoke.json"
$results += Invoke-Step "RL policy smoke" "04_rl_smoke.log" { python .\scripts\rl_smoke.py --output $rlSmokeOutput }

if ($WithDockerCompose) {
    $results += Invoke-Step "Docker Compose config" "05_docker_compose_config.log" { docker compose config --quiet }
} else {
    $skipLog = Join-Path $LogDir "05_docker_compose_config.log"
    Set-Content -LiteralPath $skipLog -Value "Skipped. Run with -WithDockerCompose to enable this check." -Encoding UTF8
    $results += [PSCustomObject]@{
        name = "Docker Compose config"
        status = "SKIP"
        log = $skipLog
    }
    Write-Host "== Docker Compose config =="
    Write-Host "[SKIP] Run with -WithDockerCompose to enable this check."
}

$results += Invoke-Step "PowerShell script parse" "06_powershell_parse.log" {
    $files = Get-ChildItem .\scripts -Filter *.ps1
    foreach ($file in $files) {
        $tokens = $null
        $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors) | Out-Null
        if ($errors -and $errors.Count -gt 0) {
            throw "PowerShell parse failed: $($file.FullName) $($errors | Out-String)"
        }
    }
}

$results += Invoke-Step "Evidence export smoke" "07_export_evidence.log" {
    $exportSmokeRoot = Join-Path $LogDir "evidence_export_smoke"
    .\scripts\export_evidence.ps1 -DashboardPort $DashboardPort -ExportRoot $exportSmokeRoot -SkipEvidenceFiles
}

$failures = @($results | Where-Object { $_.status -eq "FAIL" })
$summary = [ordered]@{
    generated_at_local = (Get-Date).ToString("o")
    project_root = $Root
    log_dir = $LogDir
    with_docker_compose = [bool]$WithDockerCompose
    passed = $failures.Count -eq 0
    results = $results
}
$summaryPath = Join-Path $LogDir "summary.json"
($summary | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $summaryPath -Encoding UTF8

$readmeLines = @(
    "# DroneRailInspection Local Verification",
    "",
    "- Generated at: $($summary.generated_at_local)",
    "- Project root: $Root",
    "- Docker Compose check: $([bool]$WithDockerCompose)",
    "- Overall passed: $($summary.passed)",
    "",
    "## Results"
)
foreach ($result in $results) {
    $readmeLines += "- $($result.status): $($result.name) -> $($result.log)"
}
$readmeLines += ""
$readmeLines += "See summary.json and the step logs for details."
Set-Content -LiteralPath (Join-Path $LogDir "README.md") -Value ($readmeLines -join [Environment]::NewLine) -Encoding UTF8

Write-Host ""
Write-Host "== Summary =="
$results | Format-Table name, status, log -AutoSize
Write-Host "Summary: $summaryPath"

if ($failures.Count -gt 0) {
    throw "Local verification failed. See $LogDir"
}

Write-Host "[PASS] Local verification complete"
