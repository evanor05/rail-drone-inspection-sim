param(
    [int]$DashboardPort = 8080,
    [string]$ExportRoot = ".\data\exports",
    [int]$MaxEvidenceFiles = 50,
    [switch]$SkipEvidenceFiles
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Resolve-ProjectPath([string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }
    return (Join-Path $Root $PathValue)
}

function Write-Utf8File([string]$PathValue, [string]$Content) {
    Set-Content -LiteralPath $PathValue -Value $Content -Encoding UTF8
}

function Invoke-Capture([scriptblock]$Block) {
    try {
        return ((& $Block) 2>&1 | Out-String).TrimEnd()
    } catch {
        return "[ERROR] $($_.Exception.Message)"
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$exportBase = Resolve-ProjectPath $ExportRoot
$exportDir = Join-Path $exportBase "inspection-evidence-$timestamp"
$reportsDir = Join-Path $exportDir "reports"
$evidenceDir = Join-Path $exportDir "evidence"
$statusDir = Join-Path $exportDir "status"

New-Item -ItemType Directory -Force -Path $reportsDir, $evidenceDir, $statusDir | Out-Null

$summary = [ordered]@{
    exported_at_local = (Get-Date).ToString("o")
    project_root = $Root
    dashboard_url = "http://127.0.0.1:$DashboardPort"
    export_dir = $exportDir
    max_evidence_files = $MaxEvidenceFiles
    copied_evidence_files = 0
    dashboard_api_reachable = $false
}

Write-Host "== Export inspection evidence package =="
Write-Host "Output: $exportDir"

Write-Host "== Copy report files =="
$reportFiles = Get-ChildItem -Path ".\data\reports" -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne ".gitkeep" }
if ($reportFiles) {
    foreach ($file in $reportFiles) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $reportsDir $file.Name) -Force
    }
    Write-Host "Copied reports: $(@($reportFiles).Count)"
} else {
    Write-Utf8File (Join-Path $reportsDir "_no_reports.txt") "No report files found under data/reports. Run offline or full acceptance first."
    Write-Host "No report files found."
}

Write-Host "== Build evidence manifest =="
$evidenceFiles = Get-ChildItem -Path ".\data\evidence" -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne ".gitkeep" } | Sort-Object LastWriteTime -Descending
$manifestRows = @()
foreach ($file in $evidenceFiles) {
    $manifestRows += [PSCustomObject]@{
        Name = $file.Name
        Length = $file.Length
        LastWriteTime = $file.LastWriteTime.ToString("o")
        SourcePath = $file.FullName
        Copied = $false
    }
}

if ((-not $SkipEvidenceFiles) -and $evidenceFiles) {
    $filesToCopy = @($evidenceFiles | Select-Object -First $MaxEvidenceFiles)
    foreach ($file in $filesToCopy) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $evidenceDir $file.Name) -Force
        foreach ($row in $manifestRows) {
            if ($row.SourcePath -eq $file.FullName) {
                $row.Copied = $true
                break
            }
        }
    }
    $summary.copied_evidence_files = @($filesToCopy).Count
    Write-Host "Copied evidence files: $($summary.copied_evidence_files)"
} elseif ($SkipEvidenceFiles) {
    Write-Utf8File (Join-Path $evidenceDir "_skipped.txt") "Evidence file copy skipped. See evidence_manifest.csv."
    Write-Host "Skipped evidence file copy."
} else {
    Write-Utf8File (Join-Path $evidenceDir "_no_evidence.txt") "No evidence files found under data/evidence. Run offline or full acceptance first."
    Write-Host "No evidence files found."
}

$manifestPath = Join-Path $exportDir "evidence_manifest.csv"
if ($manifestRows.Count -gt 0) {
    $manifestRows | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
} else {
    Write-Utf8File $manifestPath "Name,Length,LastWriteTime,SourcePath,Copied"
}

Write-Host "== Capture dashboard API snapshot =="
try {
    $status = Invoke-RestMethod -Uri "http://127.0.0.1:$DashboardPort/api/status" -TimeoutSec 3
    $dashboardStatusPath = Join-Path $statusDir "dashboard_status.json"
    $status | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $dashboardStatusPath -Encoding UTF8
    $summary.dashboard_api_reachable = $true
    Write-Host "Dashboard API reachable."
} catch {
    $dashboardErrorPath = Join-Path $statusDir "dashboard_status_error.txt"
    Write-Utf8File $dashboardErrorPath $_.Exception.Message
    Write-Host "Dashboard API unavailable: $($_.Exception.Message)"
}

Write-Host "== Capture Git, Docker, and host status =="
$gitStatusPath = Join-Path $statusDir "git_status.txt"
$gitLastCommitPath = Join-Path $statusDir "git_last_commit.txt"
$dockerPsPath = Join-Path $statusDir "docker_ps.txt"
$dockerInfoPath = Join-Path $statusDir "docker_info.txt"
$powershellVersionPath = Join-Path $statusDir "powershell_version.txt"
$hostSummaryPath = Join-Path $statusDir "host_summary.txt"
Write-Utf8File $gitStatusPath (Invoke-Capture { git status --short --branch })
Write-Utf8File $gitLastCommitPath (Invoke-Capture { git log -1 --decorate --stat })
Write-Utf8File $dockerPsPath (Invoke-Capture { docker ps -a --filter name=drone-rail-inspection --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}" })
Write-Utf8File $dockerInfoPath (Invoke-Capture { docker info })
Write-Utf8File $powershellVersionPath ($PSVersionTable | Out-String)

$hostSummaryLines = @(
    "Project root: $Root",
    "Export time: $($summary.exported_at_local)",
    "Dashboard URL: $($summary.dashboard_url)",
    "OS version: $([System.Environment]::OSVersion.VersionString)",
    "Machine name: $([System.Environment]::MachineName)",
    "User domain: $([System.Environment]::UserDomainName)"
)
$hostSummary = $hostSummaryLines -join [Environment]::NewLine
Write-Utf8File $hostSummaryPath $hostSummary

$summaryPath = Join-Path $exportDir "summary.json"
($summary | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $summaryPath -Encoding UTF8

$readmeLines = @(
    "# DroneRailInspection Evidence Package",
    "",
    "- Export time: $($summary.exported_at_local)",
    "- Project root: $Root",
    "- Dashboard: $($summary.dashboard_url)",
    "- Dashboard API reachable: $($summary.dashboard_api_reachable)",
    "- Copied evidence files: $($summary.copied_evidence_files)",
    "",
    "## Contents",
    "",
    "- reports/: JSON / Markdown / HTML inspection reports.",
    "- evidence/: copied evidence files, capped by MaxEvidenceFiles.",
    "- evidence_manifest.csv: full evidence file index.",
    "- status/: Git, Docker, Dashboard API, and host snapshots.",
    "- summary.json: machine-readable export summary.",
    "",
    "If status/dashboard_status_error.txt exists, the dashboard was not running or the port was not reachable during export."
)
$readme = $readmeLines -join [Environment]::NewLine
$exportReadmePath = Join-Path $exportDir "README.md"
Write-Utf8File $exportReadmePath $readme

Write-Host ""
Write-Host "[PASS] Evidence package generated: $exportDir"
