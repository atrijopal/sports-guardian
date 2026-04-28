# SPORTS101 DAP Platform — start all 4 servers
# Run from E:\SPORTS101 with:  .\start_all.ps1

$root = $PSScriptRoot

function Start-Module {
    param($name, $dir, $port)
    $venv = Join-Path $dir "venv"
    $pip  = Join-Path $venv "Scripts\pip.exe"
    $uvi  = Join-Path $venv "Scripts\uvicorn.exe"

    Write-Host ""
    Write-Host "==> $name (port $port)" -ForegroundColor Cyan

    if (-not (Test-Path $venv)) {
        Write-Host "    Creating venv..." -ForegroundColor Yellow
        python -m venv $venv
    }

    if (-not (Test-Path $uvi)) {
        Write-Host "    Installing dependencies..." -ForegroundColor Yellow
        & $pip install -r (Join-Path $dir "requirements.txt") --quiet
    }

    Start-Process -FilePath $uvi `
        -ArgumentList "app:app", "--host", "0.0.0.0", "--port", "$port", "--reload" `
        -WorkingDirectory $dir `
        -WindowStyle Normal
    Write-Host "    Started -> http://localhost:$port" -ForegroundColor Green
}

Start-Module "Module 1 - Video Fingerprinting" (Join-Path $root "module1-fingerprinting") 8000
Start-Module "Module 2 - Threat Intelligence"  (Join-Path $root "module2-threat-intel")   8002
Start-Module "Module 3 - Source Attribution"   (Join-Path $root "module3-watermarking")   8001
Start-Module "Hub - GUARDIAN Platform"         (Join-Path $root "hub")                    8080

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  GUARDIAN platform -> http://localhost:8080" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "All servers started. Press Ctrl+C to exit this window." -ForegroundColor Gray
Write-Host "(Server windows will keep running after you close this.)" -ForegroundColor Gray
