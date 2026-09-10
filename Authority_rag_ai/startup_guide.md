# How to Start the AI-PMS System

Follow these steps each time you restart your laptop and want to run the system.

## Step 1: Check Required Services

Before starting the application, make sure PostgreSQL and Ollama are running.

### Check PostgreSQL

Open **Command Prompt as Administrator** and run:

```cmd
net start postgresql-x64-16
```

If PostgreSQL is already running, you will see:

```text
The requested service has already been started.
```

You can confirm that PostgreSQL is running on port `5432` using:

```cmd
netstat -ano | findstr :5432
```

You should see `LISTENING` in the output.

Required PostgreSQL settings:

```text
Port: 5432
Database: pms
```

### Check Ollama

Open a normal Command Prompt and run:

```cmd
ollama list
```

Make sure the following model is shown:

```text
qwen2.5:7b
```

If the model is not installed, run:

```cmd
ollama pull qwen2.5:7b
```

If Ollama is not running, start it using:

```cmd
ollama serve
```

Keep this Command Prompt window open while using the application.

If Ollama is already running from the Windows system tray, you do not need to run `ollama serve` again.

---

## Step 2: Open the Project Folder

Open a new **Command Prompt** or **PowerShell** window.

Move to the project directory:

```cmd
cd /d D:\AI-PMS\RAG\RAG_SYSTEM
```

The `/d` option is useful in Command Prompt because it also switches from the current drive to the `D:` drive.

After running the command, your terminal should show:

```text
D:\AI-PMS\RAG\RAG_SYSTEM>
```

---

## Step 3: Start the Web Application

Run the following command:

```cmd
.\.venv\Scripts\python.exe -m uvicorn app.api_server:app --host 127.0.0.1 --port 8000
```

Wait until you see a message similar to:

```text
Uvicorn running on http://127.0.0.1:8000
```

Do not close this terminal window while using the application.

---

## Step 4: Open the Application

Open your web browser and visit:

```text
http://127.0.0.1:8000
```

The web interface and backend API will both run from the same server.

Web application:

```text
http://127.0.0.1:8000
```

API endpoints:

```text
http://127.0.0.1:8000/api/...
```

---

## How to Stop the Application

Go to the terminal where Uvicorn is running and press:

```text
Ctrl + C
```

This will stop the web server safely.

---

# Alternative: Run the Terminal Chatbot

Use this option when you want to chat through the terminal instead of using the web interface.

Open Command Prompt or PowerShell and go to the project folder:

```cmd
cd /d D:\AI-PMS\RAG\RAG_SYSTEM
```

Set the Python project path:

### Command Prompt

```cmd
set PYTHONPATH=.
```

Then start the chatbot:

```cmd
.\.venv\Scripts\python.exe scripts\rag_system_chatbot.py
```




### PowerShell

```powershell
$env:PYTHONPATH="."
```

Then start the chatbot:

```powershell
.\.venv\Scripts\python.exe scripts/rag_system_chatbot.py
```

---

# Daily Startup Summary

After restarting your laptop, run these commands in order.

### Administrator Command Prompt

```cmd
net start postgresql-x64-16
```

### Normal Command Prompt — Ollama

```cmd
ollama serve
```

Skip this command if Ollama is already running in the system tray.

### New Command Prompt — Application

```cmd
cd /d D:\AI-PMS\RAG\RAG_SYSTEM
.\.venv\Scripts\python.exe -m uvicorn app.api_server:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Common Problems

### PostgreSQL access is denied

Open Command Prompt using **Run as administrator**, then run:

```cmd
net start postgresql-x64-16
```

### Port 5432 is not listening

Check PostgreSQL:

```cmd
sc query postgresql-x64-16
```

Start it if required:

```cmd
net start postgresql-x64-16
```

### `ollama` is not recognized

Make sure Ollama is installed and restart Command Prompt after installation.

### `qwen2.5:7b` is missing

Install it using:

```cmd
ollama pull qwen2.5:7b
```

### Port 8000 is already in use

Another instance of the application may already be running. Close the old terminal or use another port:

```cmd
.\.venv\Scripts\python.exe -m uvicorn app.api_server:app --host 127.0.0.1 --port 8001
```

Then open:

```text
http://127.0.0.1:8001
```




# How to Start the AI-PMS System Using PowerShell

Follow these steps each time you restart your laptop and want to run the system.

## Step 1: Open PowerShell

Open **PowerShell as Administrator** for starting PostgreSQL:

1. Press the Windows key.
2. Search for `PowerShell`.
3. Right-click **Windows PowerShell**.
4. Select **Run as administrator**.

---

## Step 2: Start PostgreSQL

Run:

```powershell
Start-Service postgresql-x64-16
```

If PostgreSQL is already running, PowerShell may show no output. You can check its status using:

```powershell
Get-Service postgresql-x64-16
```

You should see:

```text
Status   Name                  DisplayName
------   ----                  -----------
Running  postgresql-x64-16     PostgreSQL Server 16
```

You can also check whether port `5432` is active:

```powershell
Get-NetTCPConnection -LocalPort 5432 -State Listen
```

Required PostgreSQL settings:

```text
Port: 5432
Database: pms
```

---

## Step 3: Check Ollama

Open a normal PowerShell window and run:

```powershell
ollama list
```

Make sure this model is available:

```text
qwen2.5:7b
```

If the model is missing, install it:

```powershell
ollama pull qwen2.5:7b
```

If Ollama is not running, start it:

```powershell
ollama serve
```

Keep this PowerShell window open while using the system.

If Ollama is already running from the Windows system tray, you do not need to run `ollama serve`.

---

## Step 4: Open the Project Folder

Open a new PowerShell window and run:

```powershell
Set-Location "D:\AI-PMS\RAG\RAG_SYSTEM"
```

You can also use:

```powershell
cd "D:\AI-PMS\RAG\RAG_SYSTEM"
```

Your PowerShell prompt should now show the project folder.

---

## Step 5: Start the Web Application

Run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api_server:app --host 127.0.0.1 --port 8000
```

Wait until you see:

```text
Uvicorn running on http://127.0.0.1:8000
```

Keep this PowerShell window open while using the application.

---

## Step 6: Open the Web Application

Open your browser and visit:

```text
http://127.0.0.1:8000
```

Web interface:

```text
http://127.0.0.1:8000
```

API endpoints:

```text
http://127.0.0.1:8000/api/...
```

---

## How to Stop the Application

Go to the PowerShell window where Uvicorn is running and press:

```text
Ctrl + C
```

---

# Alternative: Run the Terminal Chatbot

Open PowerShell and go to the project folder:

```powershell
cd "D:\AI-PMS\RAG\RAG_SYSTEM"
```

Set the Python project path:

```powershell
$env:PYTHONPATH="."
```

Run the chatbot:

```powershell
.\.venv\Scripts\python.exe scripts\rag_system_chatbot.py
```

---

# Daily Startup Commands

## Administrator PowerShell

Start PostgreSQL:

```powershell
Start-Service postgresql-x64-16
```

Check its status:

```powershell
Get-Service postgresql-x64-16
```

## Normal PowerShell for Ollama

```powershell
ollama serve
```

Skip this command if Ollama is already running in the system tray.

## New PowerShell for the Application

```powershell
cd "D:\AI-PMS\RAG\RAG_SYSTEM"

.\.venv\Scripts\python.exe -m uvicorn app.api_server:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

---

# Quick Startup Version

Use these commands after restarting your laptop.

### PowerShell as Administrator

```powershell
Start-Service postgresql-x64-16
```

### Normal PowerShell Window 1

```powershell
ollama serve
```

### Normal PowerShell Window 2

```powershell
cd "D:\AI-PMS\RAG\RAG_SYSTEM"

.\.venv\Scripts\python.exe -m uvicorn app.api_server:app --host 127.0.0.1 --port 8000
```

Open the application:

```text
http://127.0.0.1:8000
```
