# Start all services locally (Windows PowerShell)
# No PostgreSQL needed — uses SQLite

Write-Host "Starting Deepvue Risk Decisioning Service..." -ForegroundColor Cyan

# Set environment variables
$env:DATABASE_URL = "sqlite:///./data/deepvue.db"
$env:MOCK_UPSTREAM_URL = "http://localhost:8001"

# Start mock upstream
Write-Host "Starting mock upstream on port 8001..."
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "app:app --port 8001" -WorkingDirectory "$PSScriptRoot\mock-upstream"

Start-Sleep -Seconds 2

# Start API
Write-Host "Starting API on port 8000..."
New-Item -ItemType Directory -Force -Path "$PSScriptRoot\api\data" | Out-Null
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "app.main:app --port 8000 --reload" -WorkingDirectory "$PSScriptRoot\api"

Start-Sleep -Seconds 2

# Start frontend
Write-Host "Starting frontend on port 3000..."
Set-Location "$PSScriptRoot\frontend"
if (-not (Test-Path "node_modules")) { npm install }
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run dev"

Write-Host ""
Write-Host "Services started:" -ForegroundColor Green
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  API:       http://localhost:8000"
Write-Host "  API Docs:  http://localhost:8000/docs"
Write-Host "  Mock:      http://localhost:8001"
Write-Host ""
Write-Host "API Keys:" -ForegroundColor Yellow
Write-Host "  Kaveri: kaveri_key_deepvue_2026"
Write-Host "  Nexa:   nexa_key_deepvue_2026"
