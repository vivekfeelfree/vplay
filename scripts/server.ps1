<#
.SYNOPSIS
    vplay Web Dashboard Server Control Manager for Windows PowerShell.
.EXAMPLE
    .\scripts\server.ps1 start
    .\scripts\server.ps1 status
    .\scripts\server.ps1 stop
#>
param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "status"
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$PythonExe = if (Test-Path $VenvPython) { $VenvPython } else { "python" }
$WebScript = Join-Path $RepoRoot "scripts\web_server.py"
$PidFile = Join-Path $RepoRoot ".vplay_web.pid"

function Get-RunningProcess {
    if (Test-Path $PidFile) {
        $procId = Get-Content $PidFile -ErrorAction SilentlyContinue
        if ($procId) {
            $proc = Get-Process -Id ([int]$procId) -ErrorAction SilentlyContinue
            if ($proc) { return $proc }
        }
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
    return $null
}

function Start-VplayServer {
    Stop-VplayServer -Quiet
    Write-Host "Starting vplay Web Control Dashboard..."
    $proc = Start-Process -FilePath $PythonExe -ArgumentList "`"$WebScript`"" -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru
    $proc.Id | Set-Content -Path $PidFile
    Start-Sleep -Seconds 1
    if (-not $proc.HasExited) {
        Write-Host "Web Server is LIVE at http://localhost:8080 (PID: $($proc.Id))" -ForegroundColor Green
    } else {
        Write-Host "Failed to start server." -ForegroundColor Red
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
}

function Stop-VplayServer([switch]$Quiet) {
    $proc = Get-RunningProcess
    if ($proc) {
        if (-not $Quiet) { Write-Host "Stopping vplay Web Control Dashboard (PID: $($proc.Id))..." }
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        if (-not $Quiet) { Write-Host "Server stopped." -ForegroundColor Green }
    } elseif (-not $Quiet) {
        Write-Host "Server is not running." -ForegroundColor Yellow
    }
}

switch ($Action) {
    "start"   { Start-VplayServer }
    "stop"    { Stop-VplayServer }
    "restart" { Stop-VplayServer -Quiet; Start-VplayServer }
    "status"  {
        $proc = Get-RunningProcess
        if ($proc) {
            Write-Host "Web Server is RUNNING (PID: $($proc.Id)) -> http://localhost:8080" -ForegroundColor Green
        } else {
            Write-Host "Web Server is STOPPED" -ForegroundColor Yellow
        }
    }
}
