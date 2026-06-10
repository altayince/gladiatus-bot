# Run helper for gladiatus-bot (PowerShell)
# Usage: .\run_bot.ps1

# Check for python launcher
if (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $py = "python"
} else {
    Write-Host "Python not found. Visit https://python.org or run: winget install --id Python.Python.3" -ForegroundColor Yellow
    exit 1
}

# Create venv if missing
if (-not (Test-Path -Path .venv)) {
    & $py -3 -m venv .venv
}

# Activate venv for this session
. .\.venv\Scripts\Activate.ps1

# Upgrade pip and install requirements
& $py -3 -m pip install --upgrade pip
& $py -3 -m pip install -r requirements.txt

# Run the bot using .env values; you can override with args if needed
& $py -3 -m src.main --headless true
