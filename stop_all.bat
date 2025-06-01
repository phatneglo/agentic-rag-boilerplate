@echo off
setlocal enabledelayedexpansion

echo 🛑 Stopping Agentic RAG Full System
echo ===================================
echo.

echo 🔄 Shutting down all processes...

REM Kill Python processes related to the application
echo    🐍 Stopping Python workers and server...

REM Kill uvicorn server processes
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH ^| findstr /C:"uvicorn"') do (
    echo       Killing uvicorn server process %%i
    taskkill /PID %%i /F >nul 2>&1
)

REM Kill worker processes
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH ^| findstr /C:"app.workers"') do (
    echo       Killing worker process %%i
    taskkill /PID %%i /F >nul 2>&1
)

REM More aggressive cleanup - kill any Python process that might be related
echo    🔍 Checking for remaining Python processes...
tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH | findstr /C:"uvicorn\|app.workers\|app.main" >nul 2>&1
if not errorlevel 1 (
    echo       Found remaining processes, performing cleanup...
    REM Kill by command line pattern
    wmic process where "name='python.exe' and CommandLine like '%%uvicorn%%app.main%%'" delete >nul 2>&1
    wmic process where "name='python.exe' and CommandLine like '%%app.workers%%'" delete >nul 2>&1
)

REM Wait a moment for processes to terminate
timeout /t 2 /nobreak >nul

REM Check if any processes are still running
echo    🔍 Verifying shutdown...
set REMAINING_PROCESSES=0
for /f %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH ^| findstr /C:"uvicorn\|app.workers\|app.main" ^| find /c /v ""') do set REMAINING_PROCESSES=%%i

if !REMAINING_PROCESSES! gtr 0 (
    echo    ⚠️  Warning: !REMAINING_PROCESSES! Python processes may still be running
    echo       You may need to manually end them using Task Manager
    echo.
    echo    🔧 Manual cleanup options:
    echo       1. Open Task Manager (Ctrl+Shift+Esc^)
    echo       2. Look for Python processes in the Details tab
    echo       3. End any processes related to uvicorn or app.workers
    echo.
    tasklist /FI "IMAGENAME eq python.exe" /FO TABLE | findstr /C:"python.exe"
) else (
    echo    ✅ All application processes stopped successfully
)

echo.
echo 📁 Log files preserved in ./logs/ directory
echo    • Server log:         logs/server.log
echo    • Worker step 1 log:  logs/worker_step1.log  
echo    • Worker step 2 log:  logs/worker_step2.log
echo    • Worker step 3 log:  logs/worker_step3.log
echo    • Worker step 4 log:  logs/worker_step4.log
echo.

echo ℹ️  Note: External services (Redis, Typesense, Qdrant^) are still running
echo    Stop them manually if needed:
echo    • Redis: redis-cli shutdown
echo    • Typesense: Stop the typesense-server process
echo    • Qdrant: docker stop <qdrant_container_id>
echo.

echo ✅ Agentic RAG system shutdown complete!
echo.
pause 