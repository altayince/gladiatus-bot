# Quick Python installer via python.org
# Run as Administrator

$pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$installerPath = "$env:TEMP\python-installer.exe"

Write-Host "Downloading Python 3.11 installer..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath
    Write-Host "Running Python installer (silent mode)..." -ForegroundColor Cyan
    Start-Process -FilePath $installerPath -ArgumentList "/quiet /passive InstallAllUsers=1 PrependPath=1" -Wait
    Remove-Item $installerPath -Force
    Write-Host "Python installation complete. Close and reopen terminal, then run: .\run_full_setup.ps1" -ForegroundColor Green
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Manual install: Visit https://www.python.org/downloads and install Python 3.11+" -ForegroundColor Yellow
}
