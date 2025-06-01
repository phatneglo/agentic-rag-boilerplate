#!/bin/bash

echo "🚀 Starting Agentic RAG Full System"
echo "===================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run ./start_clean.sh first to set up the environment."
    exit 1
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating default configuration..."
    cat > .env << EOF
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Database URLs
REDIS_URL=redis://localhost:6379
TYPESENSE_URL=http://localhost:8108
QDRANT_URL=http://localhost:6333

# API Keys
TYPESENSE_API_KEY=xyz
QDRANT_API_KEY=

# Processing Configuration
MAX_RETRIES=3
WORKER_CONCURRENCY=4
CHUNK_SIZE=512
EMBEDDING_MODEL=text-embedding-3-small

# Server Configuration
DEBUG=true
LOG_LEVEL=info
EOF
    echo "   ✅ Created default .env file"
    echo "   📝 Please edit .env to add your OpenAI API key"
fi

# Service dependency check
echo ""
echo "🔧 Checking required services..."

REDIS_OK=false
TYPESENSE_OK=false
QDRANT_OK=false

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis is running"
    REDIS_OK=true
else
    echo "   ❌ Redis is not running"
fi

# Check Typesense
if curl -s http://localhost:8108/health > /dev/null 2>&1; then
    echo "   ✅ Typesense is running"
    TYPESENSE_OK=true
else
    echo "   ❌ Typesense is not running"
fi

# Check Qdrant
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo "   ✅ Qdrant is running"
    QDRANT_OK=true
else
    echo "   ❌ Qdrant is not running"
fi

# Check if critical services are missing
if [ "$REDIS_OK" = false ] || [ "$TYPESENSE_OK" = false ] || [ "$QDRANT_OK" = false ]; then
    echo ""
    echo "⚠️  MISSING REQUIRED SERVICES"
    echo "   The document processing pipeline requires all services to be running."
    echo ""
    
    if [ "$REDIS_OK" = false ]; then
        echo "   Start Redis:"
        echo "   redis-server"
        echo ""
    fi
    
    if [ "$TYPESENSE_OK" = false ]; then
        echo "   Start Typesense:"
        echo "   typesense-server --data-dir=/tmp/typesense-data --api-key=xyz --enable-cors"
        echo ""
    fi
    
    if [ "$QDRANT_OK" = false ]; then
        echo "   Start Qdrant:"
        echo "   docker run -p 6333:6333 -v \$(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant"
        echo ""
    fi
    
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Startup cancelled. Please start the required services first."
        exit 1
    fi
fi

# Create log directory
mkdir -p logs

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🔄 Shutting down all processes..."
    
    # Kill background jobs
    jobs -p | xargs -r kill
    
    # Wait a moment for graceful shutdown
    sleep 2
    
    # Force kill any remaining processes
    pkill -f "app.workers" 2>/dev/null
    pkill -f "uvicorn.*app.main" 2>/dev/null
    
    echo "✅ All processes stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo ""
echo "🚀 Starting Agentic RAG Full System..."
echo ""

# Start the FastAPI server in background
echo "📡 Starting FastAPI server..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > logs/server.log 2>&1 &
SERVER_PID=$!
echo "   ✅ Server started (PID: $SERVER_PID, logs: logs/server.log)"

# Wait a moment for server to start
sleep 3

# Start Document Converter Worker (Step 1)
echo ""
echo "🔧 Starting Document Processing Workers..."
echo "   Step 1: Document Converter Worker..."
python -m app.workers.simple_document_converter_worker > logs/worker_step1.log 2>&1 &
WORKER1_PID=$!
echo "      ✅ Started (PID: $WORKER1_PID, logs: logs/worker_step1.log)"

# Start Metadata Extractor Worker (Step 2)
echo "   Step 2: Metadata Extractor Worker..."
python -m app.workers.metadata_extractor_worker > logs/worker_step2.log 2>&1 &
WORKER2_PID=$!
echo "      ✅ Started (PID: $WORKER2_PID, logs: logs/worker_step2.log)"

# Start Typesense Indexer Worker (Step 3)
echo "   Step 3: Typesense Indexer Worker..."
python -m app.workers.typesense_indexer_worker > logs/worker_step3.log 2>&1 &
WORKER3_PID=$!
echo "      ✅ Started (PID: $WORKER3_PID, logs: logs/worker_step3.log)"

# Start Qdrant Indexer Worker (Step 4)
echo "   Step 4: Qdrant Indexer Worker..."
python -m app.workers.qdrant_indexer_worker > logs/worker_step4.log 2>&1 &
WORKER4_PID=$!
echo "      ✅ Started (PID: $WORKER4_PID, logs: logs/worker_step4.log)"

# Wait for workers to initialize
echo ""
echo "⏳ Waiting for workers to initialize..."
sleep 5

echo ""
echo "🎉 Agentic RAG Full System is now running!"
echo "========================================"
echo ""
echo "🌐 Access Points:"
echo "   • Dashboard:     http://localhost:8000/"
echo "   • AI Chat:       http://localhost:8000/chat"
echo "   • File Manager:  http://localhost:8000/file-manager"
echo "   • API Docs:      http://localhost:8000/docs"
echo "   • Typesense:     http://localhost:8108/"
echo "   • Qdrant:        http://localhost:6333/dashboard"
echo ""
echo "📊 System Status:"
echo "   • FastAPI Server:     Running (PID: $SERVER_PID)"
echo "   • Step 1 Worker:      Running (PID: $WORKER1_PID) - Document Conversion"
echo "   • Step 2 Worker:      Running (PID: $WORKER2_PID) - Metadata Extraction"
echo "   • Step 3 Worker:      Running (PID: $WORKER3_PID) - Typesense Indexing"
echo "   • Step 4 Worker:      Running (PID: $WORKER4_PID) - Qdrant RAG Indexing"
echo ""
echo "📋 Document Processing Pipeline:"
echo "   Upload → Queue → Convert → Extract → Index → RAG"
echo "      ↓      ↓        ↓         ↓        ↓      ↓"
echo "    File → Redis → Markdown → Metadata → Search → Vector Store"
echo ""
echo "📁 Log Files:"
echo "   • Server:         logs/server.log"
echo "   • Worker Step 1:  logs/worker_step1.log"
echo "   • Worker Step 2:  logs/worker_step2.log"
echo "   • Worker Step 3:  logs/worker_step3.log"
echo "   • Worker Step 4:  logs/worker_step4.log"
echo ""
echo "🔄 To monitor logs in real-time:"
echo "   tail -f logs/server.log"
echo "   tail -f logs/worker_step*.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait 