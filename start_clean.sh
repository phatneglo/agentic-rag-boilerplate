#!/bin/bash

echo "🧹 Agentic RAG - Clean Installation Script"
echo "=========================================="
echo ""
echo "This script will perform a clean installation of the Agentic RAG system."
echo "It will:"
echo "  ✅ Reset the virtual environment"
echo "  ✅ Install all Python dependencies"
echo "  ✅ Set up environment configuration"
echo "  ✅ Initialize required services"
echo "  ✅ Create necessary collections and indexes"
echo ""

# Confirmation prompt
read -p "⚠️  WARNING: This will remove your existing virtual environment and reset configurations. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Installation cancelled."
    exit 1
fi

echo ""
echo "🚀 Starting clean installation..."
echo ""

# Step 1: Clean up existing virtual environment
echo "📁 Step 1: Cleaning up existing virtual environment..."
if [ -d "venv" ]; then
    rm -rf venv
    echo "   ✅ Removed existing virtual environment"
else
    echo "   ℹ️  No existing virtual environment found"
fi

# Step 2: Create new virtual environment
echo ""
echo "🐍 Step 2: Creating new virtual environment..."
python3 -m venv venv
if [ $? -eq 0 ]; then
    echo "   ✅ Virtual environment created successfully"
else
    echo "   ❌ Failed to create virtual environment"
    exit 1
fi

# Step 3: Activate virtual environment and install dependencies
echo ""
echo "📦 Step 3: Installing Python dependencies..."
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo "   ✅ Dependencies installed successfully"
else
    echo "   ❌ Failed to install dependencies"
    exit 1
fi

# Step 4: Environment configuration
echo ""
echo "⚙️  Step 4: Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   ✅ Created .env file from .env.example"
    else
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

# Collection Names
TYPESENSE_COLLECTION_NAME=documents
QDRANT_COLLECTION_NAME=documents_rag

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
    fi
else
    echo "   ℹ️  .env file already exists, skipping..."
fi

# Step 5: Check required services
echo ""
echo "🔧 Step 5: Checking required services..."

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis is running"
else
    echo "   ❌ Redis is not running. Please start Redis:"
    echo "      brew services start redis  # macOS with Homebrew"
    echo "      sudo systemctl start redis  # Linux with systemd"
    echo "      redis-server  # Manual start"
fi

# Check Typesense
if curl -s http://localhost:8108/health > /dev/null 2>&1; then
    echo "   ✅ Typesense is running"
else
    echo "   ❌ Typesense is not running. Please start Typesense:"
    echo "      typesense-server --data-dir=/tmp/typesense-data --api-key=xyz --enable-cors"
fi

# Check Qdrant
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo "   ✅ Qdrant is running"
else
    echo "   ❌ Qdrant is not running. Please start Qdrant:"
    echo "      docker run -p 6333:6333 -v \$(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant"
fi

# Step 6: Initialize collections (if services are running)
echo ""
echo "🗄️  Step 6: Initializing collections and indexes..."

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    set -a  # Automatically export all variables
    source .env
    set +a  # Stop automatic export
fi

# Load collection names from .env file
TYPESENSE_COLLECTION_NAME=${TYPESENSE_COLLECTION_NAME:-documents}
QDRANT_COLLECTION_NAME=${QDRANT_COLLECTION_NAME:-documents_rag}

# Create Typesense collection
if curl -s http://localhost:8108/health > /dev/null 2>&1; then
    # Check if collection exists
    if curl -s "http://localhost:8108/collections/${TYPESENSE_COLLECTION_NAME}" -H "X-TYPESENSE-API-KEY: xyz" > /dev/null 2>&1; then
        echo "   ℹ️  Typesense '${TYPESENSE_COLLECTION_NAME}' collection already exists"
    else
        # Create collection with auto-embedding
        curl -X POST 'http://localhost:8108/collections' \
            -H 'X-TYPESENSE-API-KEY: xyz' \
            -H 'Content-Type: application/json' \
            -d "{
                \"name\": \"${TYPESENSE_COLLECTION_NAME}\",
                \"enable_nested_fields\": true,
                \"fields\": [
                    {\"name\": \"id\", \"type\": \"string\"},
                    {\"name\": \"title\", \"type\": \"string\"},
                    {\"name\": \"description\", \"type\": \"string\"},
                    {\"name\": \"tags\", \"type\": \"string[]\"},
                    {\"name\": \"file_path\", \"type\": \"string\"},
                    {\"name\": \"file_type\", \"type\": \"string\"},
                    {\"name\": \"created_at\", \"type\": \"string\"},
                    {\"name\": \"user_id\", \"type\": \"string\"},
                    {\"name\": \"embedding\", \"type\": \"float[]\", \"embed\": {\"from\": [\"title\", \"description\"], \"model_config\": {\"model_name\": \"openai/text-embedding-3-small\"}}}
                ]
            }" > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            echo "   ✅ Typesense '${TYPESENSE_COLLECTION_NAME}' collection created with auto-embedding"
        else
            echo "   ⚠️  Could not create Typesense collection (check OpenAI API key)"
        fi
    fi
else
    echo "   ⚠️  Skipping Typesense collection setup (service not running)"
fi

# Create Qdrant collection
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    # Check if collection exists
    if curl -s "http://localhost:6333/collections/${QDRANT_COLLECTION_NAME}" > /dev/null 2>&1; then
        echo "   ℹ️  Qdrant '${QDRANT_COLLECTION_NAME}' collection already exists"
    else
        # Create collection with named vectors
        curl -X PUT "http://localhost:6333/collections/${QDRANT_COLLECTION_NAME}" \
            -H 'Content-Type: application/json' \
            -d '{
                "vectors": {
                    "text-dense": {"size": 1536, "distance": "Cosine"}
                }
            }' > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            echo "   ✅ Qdrant '${QDRANT_COLLECTION_NAME}' collection created with named vectors"
        else
            echo "   ⚠️  Could not create Qdrant collection"
        fi
    fi
else
    echo "   ⚠️  Skipping Qdrant collection setup (service not running)"
fi

echo ""
echo "🎉 Installation Complete!"
echo "======================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your OpenAI API key:"
echo "   nano .env"
echo ""
echo "2. Start the required services (if not already running):"
echo "   - Redis: redis-server"
echo "   - Typesense: typesense-server --data-dir=/tmp/typesense-data --api-key=xyz --enable-cors"
echo "   - Qdrant: docker run -p 6333:6333 -v \$(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant"
echo ""
echo "3. Choose your startup option:"
echo "   ./start_server.sh                    # Server only (development)"
echo "   ./start_server_and_workers.sh        # Full system (recommended)"
echo ""
echo "4. Access the application:"
echo "   - Dashboard: http://localhost:8000/"
echo "   - Chat: http://localhost:8000/chat"
echo "   - File Manager: http://localhost:8000/file-manager"
echo "   - API Docs: http://localhost:8000/docs"
echo ""

deactivate 