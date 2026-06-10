# Full setup for gladiatus-bot (attempts to install Python & Chrome via winget, then runs run_bot.ps1)
# Run this script as Administrator: right-click PowerShell -> Run as Administrator

function Is-Admin {
    $current = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $current.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Is-Admin)) {
    Write-Host "This script needs administrator privileges. Relaunching as admin..." -ForegroundColor Yellow
    Start-Process -FilePath pwsh -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File \"$PSCommandPath\"" -Verb RunAs
    exit
}

# Ensure winget exists
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "winget not found. Ensure you are on Windows 10/11 with winget installed. Alternative: Install Python manually from python.org" -ForegroundColor Yellow
} else {
    # Install Python if missing
    if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "Python not found - installing via winget..." -ForegroundColor Cyan
        winget install --id Python.Python.3 -e --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "Python already installed." -ForegroundColor Green
    }

    # Install Google Chrome if missing
    if (-not (Test-Path "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe") -and -not (Get-Command chrome -ErrorAction SilentlyContinue)) {
        Write-Host "Chrome not found - installing via winget..." -ForegroundColor Cyan
        winget install --id Google.Chrome -e --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "Chrome already installed." -ForegroundColor Green
    }
}

# After ensuring prerequisites, call run_bot.ps1 to create venv, install deps and run
Write-Host "Prerequisites step complete. Running run_bot.ps1..." -ForegroundColor Cyan

# Allow execution of run_bot.ps1 in this session
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force

$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath 'run_bot.ps1'
if (Test-Path $scriptPath) {
    & $scriptPath
} else {
    Write-Host "run_bot.ps1 not found." -ForegroundColor Red
}
