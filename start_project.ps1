# Port Land Lease MMS — All-in-One Project Starter Script
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -ErrorAction SilentlyContinue

$ProjectRoot = "C:\Users\Asus\Downloads\port-land-lease-mms"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Starting Port Land Lease MMS System..." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

# Terminal 1: Backend FastAPI (Port 5000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot'; .\venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 5000 --reload"

# Terminal 2: Streamlit Active Thread (Port 8501)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot'; .\venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501"

# Terminal 3: Frontend React (Port 3000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\port-lease-mms'; npm run dev"

Write-Host "`nAll 3 Servers launched successfully!" -ForegroundColor Green
Write-Host "Backend API:        http://localhost:5000" -ForegroundColor Yellow
Write-Host "Streamlit Thread:   http://localhost:8501" -ForegroundColor Yellow
Write-Host "Frontend Web:       http://localhost:3000" -ForegroundColor Yellow
Write-Host "`nTenant Login:       http://localhost:3000/tenant/login" -ForegroundColor White
Write-Host "Tenant Thread UI:   http://localhost:3000/tenant/discussion" -ForegroundColor White
Write-Host "Authority Login:    http://localhost:3000/authority/login" -ForegroundColor White
