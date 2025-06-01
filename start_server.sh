#!/bin/bash

echo "🚀 Starting Agentic RAG Server"
echo "=============================="
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

# Quick service check
echo ""
echo "🔧 Checking service dependencies..."

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis is running"
else
    echo "   ⚠️  Redis is not running (queue functionality will be limited)"
    echo "      To start Redis: redis-server"
fi

# Check Typesense
if curl -s http://localhost:8108/health > /dev/null 2>&1; then
    echo "   ✅ Typesense is running"
else
    echo "   ⚠️  Typesense is not running (search functionality will be limited)"
    echo "      To start Typesense: typesense-server --data-dir=/tmp/typesense-data --api-key=xyz --enable-cors"
fi

# Check Qdrant
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo "   ✅ Qdrant is running"
else
    echo "   ⚠️  Qdrant is not running (RAG functionality will be limited)"
    echo "      To start Qdrant: docker run -p 6333:6333 -v \$(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant"
fi

echo ""
echo "🌐 Starting FastAPI server..."
echo "   Server will be available at: http://localhost:8000"
echo "   API documentation at: http://localhost:8000/docs"
echo ""
echo "📝 Note: This starts ONLY the web server."
echo "   For full document processing capabilities, use ./start_server_and_workers.sh"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the FastAPI server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 