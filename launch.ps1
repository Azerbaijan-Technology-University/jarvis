# Get the directory where this script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Define the path to the activation script
$activatePath = ".\.venv\Scripts\Activate.ps1"

# Check if the venv exists, then activate and run
if (Test-Path $activatePath) {
    & $activatePath
    python main.py
} else {
    Write-Host "Error: Virtual environment not found at $activatePath" -ForegroundColor Red
}
    