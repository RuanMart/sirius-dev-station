# Sirius Dev Station — PowerShell Start Script
$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Magenta
Write-Host "   Sirius Dev Station — Local Control Plane    " -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Magenta

$VenvDir = Join-Path $PSScriptRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment not found. Setting up with uv..." -ForegroundColor Yellow
    uv venv
    uv pip install -r requirements.txt python-dotenv
}

$Port = 8080
if ($args.Count -gt 0) {
    $Port = [int]$args[0]
}

Write-Host "Server starting on http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

# Start uvicorn server
& $VenvPython server.py --host 127.0.0.1 --port $Port
