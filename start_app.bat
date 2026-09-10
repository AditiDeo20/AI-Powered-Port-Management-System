@echo off
TITLE AI-PMS Master Application Launcher
echo ======================================================================
echo                  AI-PMS MASTER MULTI-SERVICE LAUNCHER                  
echo ======================================================================

echo [Step 1/5] Cleaning up zombie socket processes on ports 8000 and 3000...
venv\Scripts\python.exe backend\cleanup_ports.py

echo [Step 2/5] Checking and starting Ollama background AI service...
start /min "" ollama serve >nul 2>&1

echo [Step 3/5] Starting FastAPI Backend API Server on 0.0.0.0:8000...
start "AI-PMS Backend (Port 8000)" cmd /k "cd backend && ..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [Step 4/5] Starting Next.js Web Frontend on http://localhost:3000...
start "AI-PMS Frontend (Port 3000)" cmd /k "cd port-lease-mms && npm.cmd run dev"

echo [Step 5/5] Waiting 6 seconds for server initialization...
ping 127.0.0.1 -n 7 >nul

echo Auto-launching browser to http://localhost:3000/ ...
start http://localhost:3000/

echo ======================================================================
echo          AI-PMS APPLICATION SUITE IS ACTIVE AND OPERATIONAL!          
echo ======================================================================
