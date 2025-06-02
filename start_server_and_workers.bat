@echo off
setlocal enabledelayedexpansion

echo 🚀 Starting Agentic RAG Full System
echo ====================================
echo.

REM Check if conda environment exists
conda info --envs | findstr /C:"agentic-rag" >nul 2>&1
if errorlevel 1 (
    echo ❌ Conda environment 'agentic-rag' not found!
    echo    Please run 'conda activate agentic-rag' first or create the environment.
    pause
    exit /b 1
)

REM Activate conda environment
echo 🐍 Activating conda environment...
call conda activate agentic-rag

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️  .env file not found. Creating default configuration...
    (
        echo # OpenAI Configuration
        echo OPENAI_API_KEY=your_openai_api_key_here
        echo.
        echo # Database URLs
        echo REDIS_URL=redis://localhost:6379
        echo TYPESENSE_URL=http://localhost:8108
        echo QDRANT_URL=http://localhost:6333
        echo.
        echo # API Keys
        echo TYPESENSE_API_KEY=xyz
        echo QDRANT_API_KEY=
        echo.
        echo # Collection Names
        echo TYPESENSE_COLLECTION_NAME=documents
        echo QDRANT_COLLECTION_NAME=documents_rag
        echo.
        echo # Processing Configuration
        echo MAX_RETRIES=3
        echo WORKER_CONCURRENCY=4
        echo CHUNK_SIZE=512
        echo EMBEDDING_MODEL=text-embedding-3-small
        echo.
        echo # Server Configuration
        echo DEBUG=true
        echo LOG_LEVEL=info
    ) > .env
    echo    ✅ Created default .env file
    echo    📝 Please edit .env to add your OpenAI API key
)

REM Service dependency check
echo.
echo 🔧 Checking required services...

set REDIS_OK=false
set TYPESENSE_OK=false
set QDRANT_OK=false

REM Check Redis
redis-cli ping >nul 2>&1
if not errorlevel 1 (
    echo    ✅ Redis is running
    set REDIS_OK=true
) else (
    echo    ❌ Redis is not running
)

REM Check Typesense
curl -s http://localhost:8108/health >nul 2>&1
if not errorlevel 1 (
    echo    ✅ Typesense is running
    set TYPESENSE_OK=true
) else (
    echo    ❌ Typesense is not running
)

REM Check Qdrant
curl -s http://localhost:6333/collections >nul 2>&1
if not errorlevel 1 (
    echo    ✅ Qdrant is running
    set QDRANT_OK=true
) else (
    echo    ❌ Qdrant is not running
)

REM Check if critical services are missing
if "%REDIS_OK%"=="false" goto :missing_services
if "%TYPESENSE_OK%"=="false" goto :missing_services
if "%QDRANT_OK%"=="false" goto :missing_services
goto :services_ok

:missing_services
echo.
echo ⚠️  MISSING REQUIRED SERVICES
echo    The document processing pipeline requires all services to be running.
echo.

if "%REDIS_OK%"=="false" (
    echo    Start Redis:
    echo    redis-server
    echo.
)

if "%TYPESENSE_OK%"=="false" (
    echo    Start Typesense:
    echo    typesense-server --data-dir=/tmp/typesense-data --api-key=xyz --enable-cors
    echo.
)

if "%QDRANT_OK%"=="false" (
    echo    Start Qdrant:
    echo    docker run -p 6333:6333 -v %cd%/qdrant_storage:/qdrant/storage qdrant/qdrant
    echo.
)

set /p "continue=Do you want to continue anyway? (y/N): "
if /i not "%continue%"=="y" (
    echo ❌ Startup cancelled. Please start the required services first.
    pause
    exit /b 1
)

:services_ok
REM Create log directory
if not exist "logs" mkdir logs

REM Check for existing processes
echo.
echo 🔍 Checking for existing worker processes...
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /C:"uvicorn" /C:"app.workers" >nul 2>&1
if not errorlevel 1 (
    echo    ⚠️  Found existing Python worker/server processes
    echo    These may cause 'Worker is already running' conflicts.
    echo    Options:
    echo    1. Kill them manually using Task Manager
    echo    2. Use different port: python -m uvicorn app.main:app --port 8001
    echo    3. Continue anyway (may see error messages but workers will function^)
    echo.
    
    set /p "continue=Continue anyway? (y/N): "
    if /i not "!continue!"=="y" (
        echo ❌ Startup cancelled.
        echo    To kill existing processes: Use Task Manager to end Python processes
        pause
        exit /b 1
    )
    
    echo    ⚡ Continuing... (ignoring BullMQ 'already running' errors^)
)

echo.
echo 🚀 Starting Agentic RAG Full System...
echo.

REM Start the FastAPI server in background
echo 📡 Starting FastAPI server...

REM Check if port 8000 is busy
netstat -an | findstr ":8000 " >nul 2>&1
if not errorlevel 1 (
    set SERVER_PORT=8001
    echo    ⚠️  Port 8000 is busy, using port !SERVER_PORT!
) else (
    set SERVER_PORT=8000
)

REM Start server in background
start /B python -m uvicorn app.main:app --reload --reload-exclude="logs/*" --reload-exclude="*.log" --reload-exclude="file_storage/*" --reload-exclude="uploads/*" --reload-exclude="processed/*" --host 0.0.0.0 --port %SERVER_PORT% > logs/server.log 2>&1
echo    ✅ Server started (logs: logs/server.log^)

REM Wait a moment for server to start
timeout /t 3 /nobreak >nul

REM Start Document Processing Workers
echo.
echo 🔧 Starting Document Processing Workers...
echo    Step 1: Document Converter Worker...
start /B python -m app.workers.simple_document_converter_worker > logs/worker_step1.log 2>&1
echo       ✅ Started (logs: logs/worker_step1.log^)

echo    Step 2: Metadata Extractor Worker...
start /B python -m app.workers.metadata_extractor_worker > logs/worker_step2.log 2>&1
echo       ✅ Started (logs: logs/worker_step2.log^)

echo    Step 3: Typesense Indexer Worker...
start /B python -m app.workers.typesense_indexer_worker > logs/worker_step3.log 2>&1
echo       ✅ Started (logs: logs/worker_step3.log^)

echo    Step 4: Qdrant Indexer Worker...
start /B python -m app.workers.qdrant_indexer_worker > logs/worker_step4.log 2>&1
echo       ✅ Started (logs: logs/worker_step4.log^)

REM Wait for workers to initialize
echo.
echo ⏳ Waiting for workers to initialize...
timeout /t 5 /nobreak >nul

echo.
echo 🎉 Agentic RAG Full System is now running!
echo ========================================
echo.
echo 🌐 Access Points:
echo    • Dashboard:     http://localhost:%SERVER_PORT%/
echo    • AI Chat:       http://localhost:%SERVER_PORT%/chat
echo    • File Manager:  http://localhost:%SERVER_PORT%/file-manager
echo    • API Docs:      http://localhost:%SERVER_PORT%/docs
echo    • Typesense:     http://localhost:8108/
echo    • Qdrant:        http://localhost:6333/dashboard
echo.
echo 📊 System Status:
echo    • FastAPI Server:     Running on port %SERVER_PORT%
echo    • Step 1 Worker:      Running - Document Conversion
echo    • Step 2 Worker:      Running - Metadata Extraction
echo    • Step 3 Worker:      Running - Typesense Indexing
echo    • Step 4 Worker:      Running - Qdrant RAG Indexing
echo.
echo 📋 Document Processing Pipeline:
echo    Upload → Queue → Convert → Extract → Index → RAG
echo       ↓      ↓        ↓         ↓        ↓      ↓
echo     File → Redis → Markdown → Metadata → Search → Vector Store
echo.
echo 📁 Log Files:
echo    • Server:         logs/server.log
echo    • Worker Step 1:  logs/worker_step1.log
echo    • Worker Step 2:  logs/worker_step2.log
echo    • Worker Step 3:  logs/worker_step3.log
echo    • Worker Step 4:  logs/worker_step4.log
echo.
echo 🔄 To monitor logs in real-time:
echo    PowerShell: Get-Content logs/server.log -Wait
echo    Command Prompt: type logs/server.log
echo.
echo ℹ️  Note: BullMQ 'Worker is already running' errors are usually harmless
echo    if workers are functioning. Check logs for actual processing errors.
echo.
echo Press Ctrl+C to stop, or close this window to leave services running
echo.

REM Keep the window open and wait for user input
:wait_loop
timeout /t 1 /nobreak >nul
goto wait_loop 