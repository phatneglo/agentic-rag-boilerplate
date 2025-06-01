# Agentic RAG - AI Document Processing & Chat System

A complete AI-powered document processing and chat system with a sophisticated 4-step pipeline for document conversion, metadata extraction, search indexing, and RAG (Retrieval-Augmented Generation) capabilities.

## 🚀 Features

### 📄 Document Processing Pipeline
- **4-Step Processing Pipeline** with BullMQ queue management:
  1. **Document Conversion**: PDF/DOCX/TXT/HTML → Markdown using Marker
  2. **Metadata Extraction**: AI-powered metadata extraction using LlamaIndex
  3. **Search Indexing**: Auto-embedding and indexing to Typesense
  4. **RAG Integration**: Vector storage in Qdrant for intelligent retrieval

### 🔍 Search & RAG Capabilities
- **Typesense Search**: Fast, typo-tolerant search with auto-embedding (OpenAI text-embedding-3-small)
- **Qdrant Vector Store**: Hybrid search support with dense and sparse vectors
- **LlamaIndex Integration**: Advanced document chunking and retrieval
- **Real-time Processing**: Background workers for parallel document processing

### 💬 AI Chat Interface
- **Claude-inspired design** with modern, responsive UI
- **Real-time WebSocket communication** for instant responses
- **RAG-powered responses** using processed documents
- **Artifacts system** supporting:
  - Code snippets with syntax highlighting (Prism.js)
  - Mermaid diagrams and flowcharts
  - HTML/Markdown rendering
  - JSON formatting and validation
- **File upload support** with drag-and-drop functionality
- **Chat history** with session management
- **Export capabilities** (JSON, TXT formats)

### 📁 File Manager
- **Web-based file browser** with grid and list views
- **Upload/download** with progress tracking
- **Document processing** integration
- **Folder management** (create, rename, move, delete)
- **Search functionality** across files and folders
- **Drag-and-drop** file operations

### 📊 Dashboard
- **AdminLTE-themed dashboard** with real-time system monitoring
- **API health monitoring** with live status updates
- **Processing queue status** and worker monitoring
- **Document processing metrics** and statistics
- **File storage metrics** and usage statistics

## 🏗️ System Architecture

### Document Processing Pipeline
```
Upload → Queue → Worker 1 → Worker 2 → Worker 3 → Worker 4
  ↓        ↓         ↓         ↓         ↓         ↓
File → Redis → Convert → Extract → Index → RAG
             (Marker)  (LlamaIndex) (Typesense) (Qdrant)
```

### Service Stack
- **FastAPI** - High-performance async API server
- **Redis** - Queue management and caching
- **Typesense** - Search engine with auto-embedding
- **Qdrant** - Vector database for RAG
- **BullMQ** - Background job processing
- **LlamaIndex** - Document processing and RAG framework

## 📁 Project Structure

```
agentic-rag/
├── app/                          # Backend FastAPI application
│   ├── api/routes/              # API route handlers
│   │   ├── chat_routes.py       # Chat API endpoints
│   │   ├── document_routes.py   # Document processing
│   │   ├── file_manager.py      # File management API
│   │   └── file_routes.py       # File upload/download
│   ├── workers/                 # Background processing workers
│   │   ├── simple_document_converter_worker.py  # Step 1: Conversion
│   │   ├── metadata_extractor_worker.py         # Step 2: Metadata
│   │   ├── typesense_indexer_worker.py          # Step 3: Search indexing
│   │   └── qdrant_indexer_worker.py             # Step 4: RAG indexing
│   ├── services/                # Business logic services
│   │   ├── document_converter_service.py        # Document conversion
│   │   ├── typesense_indexer_service.py         # Typesense operations
│   │   ├── qdrant_indexer_service.py            # Qdrant operations
│   │   └── object_storage_service.py            # File storage
│   ├── core/                    # Core configuration
│   ├── models/                  # Pydantic models
│   └── main.py                  # Main FastAPI application
├── static/modules/              # Frontend modules
│   ├── chat/                    # AI Chat Interface
│   ├── dashboard/               # Main Dashboard
│   └── file-manager/           # File Manager
├── start_clean.sh              # Clean installation script
├── start_server.sh             # Server-only startup
├── start_server_and_workers.sh # Full system startup
└── requirements.txt            # Python dependencies
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- Redis 6.0+
- Typesense 0.25.0+
- Qdrant 1.7.0+
- OpenAI API Key (for embeddings)

### Quick Start

#### Option 1: Clean Installation
```bash
./start_clean.sh
```
This will guide you through a complete reset and installation.

#### Option 2: Manual Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agentic-rag
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key and other settings
   ```

5. **Start required services**
   ```bash
   # Redis
   redis-server
   
   # Typesense
   typesense-server --data-dir=/tmp/typesense-data --api-key=xyz --enable-cors
   
   # Qdrant
   docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
   ```

## 🚀 Running the Application

### Option 1: Server Only
```bash
./start_server.sh
```
Starts only the FastAPI server (for development/testing).

### Option 2: Full System (Recommended)
```bash
./start_server_and_workers.sh
```
Starts the FastAPI server + all 4 background workers for complete functionality.

### Manual Startup
```bash
# Activate virtual environment
source venv/bin/activate

# Start the main server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In separate terminals, start workers:
python -m app.workers.simple_document_converter_worker
python -m app.workers.metadata_extractor_worker
python -m app.workers.typesense_indexer_worker
python -m app.workers.qdrant_indexer_worker
```

## 🌐 Access Points

- **Dashboard**: http://localhost:8000/
- **AI Chat**: http://localhost:8000/chat
- **File Manager**: http://localhost:8000/file-manager
- **API Documentation**: http://localhost:8000/docs
- **Typesense**: http://localhost:8108/
- **Qdrant**: http://localhost:6333/dashboard

## 💻 Usage

### Document Processing Workflow
1. **Upload Documents**: Use File Manager or API to upload PDF/DOCX/TXT/HTML files
2. **Automatic Processing**: Files are queued and processed through 4 steps:
   - Converted to Markdown using Marker
   - Metadata extracted using LlamaIndex AI
   - Indexed to Typesense with auto-embeddings
   - Stored in Qdrant for RAG capabilities
3. **Search & Query**: Use Typesense for fast search or chat for RAG queries

### AI Chat with RAG
1. Navigate to the Chat interface
2. Upload documents or reference existing processed documents
3. Ask questions about your documents
4. Get AI responses enhanced with relevant document context
5. View source citations and document excerpts

### Search Interface
1. Use Typesense dashboard or API for direct search
2. Query by title, description, tags, or content
3. Get ranked results with auto-embedding similarity

## 🔌 API Endpoints

### Document Processing API
- `POST /api/v1/files/upload` - Upload and queue documents for processing
- `GET /api/v1/documents/status/{document_id}` - Check processing status
- `GET /api/v1/documents/search` - Search processed documents

### Chat API
- `POST /api/v1/chat/message` - Send chat message with RAG
- `WS /ws/chat` - WebSocket endpoint for real-time chat
- `GET /api/v1/chat/history` - Get chat history

### File Management API
- `GET /api/v1/file-manager/` - List files and folders
- `POST /api/v1/file-manager/upload` - Upload files
- `DELETE /api/v1/file-manager/item` - Delete files/folders

### System API
- `GET /health` - System health check
- `GET /api/v1/system/status` - Processing queue status

## ⚙️ Configuration

### Environment Variables
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Database URLs
REDIS_URL=redis://localhost:6379
TYPESENSE_URL=http://localhost:8108
QDRANT_URL=http://localhost:6333

# API Keys
TYPESENSE_API_KEY=xyz
QDRANT_API_KEY=your_qdrant_key

# Processing Configuration
MAX_RETRIES=3
WORKER_CONCURRENCY=4
CHUNK_SIZE=512
EMBEDDING_MODEL=text-embedding-3-small
```

### Service Configuration

#### Typesense Setup
```bash
# Auto-embedding with OpenAI
curl -X POST 'http://localhost:8108/collections' \
  -H 'X-TYPESENSE-API-KEY: xyz' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "documents",
    "enable_nested_fields": true,
    "fields": [
      {"name": "title", "type": "string"},
      {"name": "description", "type": "string"},
      {"name": "tags", "type": "string[]"},
      {"name": "embedding", "type": "float[]", "embed": {"from": ["title", "description"], "model_config": {"model_name": "openai/text-embedding-3-small"}}}
    ]
  }'
```

#### Qdrant Collection Setup
```bash
# Named vectors for hybrid search
curl -X PUT 'http://localhost:6333/collections/documents' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "text-dense": {"size": 1536, "distance": "Cosine"},
      "text-sparse": {"size": 1024, "distance": "Dot"}
    }
  }'
```

## 🔧 Processing Pipeline Details

### Step 1: Document Conversion
- **Input**: PDF, DOCX, TXT, HTML files
- **Output**: Clean Markdown text
- **Technology**: Marker (PDFs), python-docx (DOCX), BeautifulSoup (HTML)
- **Features**: OCR support, table preservation, image handling

### Step 2: Metadata Extraction
- **Input**: Markdown content
- **Output**: Structured metadata (title, description, tags, summary)
- **Technology**: LlamaIndex with OpenAI GPT models
- **Features**: AI-powered content analysis, automatic tagging

### Step 3: Typesense Indexing
- **Input**: Metadata JSON
- **Output**: Searchable index with embeddings
- **Technology**: Typesense with OpenAI embeddings
- **Features**: Auto-embedding, typo tolerance, faceted search

### Step 4: Qdrant RAG Integration
- **Input**: Markdown content + metadata
- **Output**: Vector embeddings for RAG
- **Technology**: LlamaIndex + Qdrant
- **Features**: Document chunking, hybrid search, similarity retrieval

## 🚧 Development Status

### ✅ Completed Features
- [x] 4-step document processing pipeline
- [x] BullMQ queue management with Redis
- [x] Typesense integration with auto-embedding
- [x] Qdrant vector storage with LlamaIndex
- [x] Worker-based background processing
- [x] File upload and storage management
- [x] RAG-powered chat interface
- [x] Real-time WebSocket communication
- [x] System health monitoring
- [x] Complete test suite

### 🔧 In Progress
- [ ] Hybrid search implementation (pending PyTorch 2.6+)
- [ ] Advanced document preprocessing
- [ ] Multi-tenant support
- [ ] Performance optimizations

### 📋 Roadmap
- [ ] Document versioning
- [ ] Advanced analytics dashboard
- [ ] Custom embedding models
- [ ] Batch processing optimization
- [ ] Multi-language support

## 🧪 Testing

### Run Pipeline Tests
```bash
# Test complete pipeline
python test_complete_pipeline.py

# Test individual components
python -m pytest tests/

# Check service health
curl http://localhost:8000/health
```

### Verify Processing
```bash
# Check Typesense documents
curl 'http://localhost:8108/collections/documents/documents/search?q=*'

# Check Qdrant points
curl 'http://localhost:6333/collections/documents/points/count'

# Monitor Redis queues
redis-cli keys "*bull*"
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LlamaIndex** for the RAG framework
- **Typesense** for fast search capabilities
- **Qdrant** for vector storage
- **Marker** for PDF processing
- **FastAPI** for the web framework
- **BullMQ** for queue management 