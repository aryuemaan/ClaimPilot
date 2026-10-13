# One command local run (Windows PowerShell):  powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path "backend\.venv")) {
  Write-Host "==> Creating Python virtualenv"
  python -m venv backend\.venv
}
& backend\.venv\Scripts\Activate.ps1
Write-Host "==> Installing Python packages"
python -m pip install -q --upgrade pip
pip install -q -r backend\requirements.txt

if (-not (Test-Path "frontend\dist\index.html") -or $env:REBUILD -eq "1") {
  Write-Host "==> Building the web app"
  Push-Location frontend
  npm install --no-audit --no-fund
  npm run build
  Pop-Location
}

if (-not (Test-Path ".env")) { Copy-Item .env.example .env }
Push-Location backend
Write-Host "==> Checking configuration"
python -m app.doctor
Write-Host ""
Write-Host "==> ClaimPilot running at http://localhost:8080  (customer app: /claim, console: /console)"
uvicorn app.main:app --host 0.0.0.0 --port 8080
