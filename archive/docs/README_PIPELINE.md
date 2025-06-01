# Document Processing Pipeline

A comprehensive 4-step document processing and indexing pipeline built with FastAPI, LlamaIndex, and modern AI technologies.

## Overview

This pipeline processes documents through four distinct stages:

1. **Document-to-Markdown Conversion** using Marker library
2. **Metadata Extraction** using LlamaIndex with structured output
3. **Typesense Indexing** with metadata and embeddings for search
4. **Qdrant Integration** for RAG (Retrieval Augmented Generation) using LlamaIndex

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Step 1: Conv   │───▶│ Step 2: Meta    │───▶│ Step 3: Typsns  │───▶│ Step 4: Qdrant  │
│  (Marker)       │    │ (LlamaIndex)    │    │ (Search Index)  │    │ (RAG Index)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │                       │
        ▼                       ▼                       ▼                       ▼
  Markdown File          JSON Metadata           Typesense Doc          Qdrant Vectors
```

## Features

- **Multi-format Support**: PDF, DOCX, PPTX, XLSX, EPUB, HTML, TXT, MD
- **Async Processing**: Redis queues with BullMQ for scalable job processing
- **AI-Powered**: OpenAI embeddings and LLM-based metadata extraction
- **Dual Indexing**: Typesense for search + Qdrant for RAG
- **Robust Error Handling**: Comprehensive logging and fallback mechanisms
- **RESTful API**: Complete HTTP API with status tracking
- **Type Safety**: Full Pydantic models with validation

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 2. Required Services

Start the required external services:

```bash
# Redis (for queues)
redis-server

# Typesense (for search indexing)
docker run -p 8108:8108 -v/tmp/typesense-data:/data typesense/typesense:0.25.2 \
  --data-dir /data --api-key=xyz --enable-cors

# Qdrant (for vector storage)
docker run -p 6333:6333 qdrant/qdrant
```

### 3. Start the Application

```bash
# Start the main API server
python -m app.main

# In separate terminals, start the workers:
python -m app.workers.document_converter_worker
python -m app.workers.metadata_extractor_worker
python -m app.workers.typesense_indexer_worker
python -m app.workers.qdrant_indexer_worker
```

### 4. Test the Pipeline

```bash
# Run the test script
python test_pipeline.py
```

## API Endpoints

### Document Processing Pipeline

- `POST /api/v1/document-processing/process` - Upload and process document
- `GET /api/v1/document-processing/status/{document_id}` - Get processing status
- `POST /api/v1/document-processing/process-file-path` - Process by file path
- `GET /api/v1/document-processing/health` - Pipeline health check

### Example Usage

```bash
# Upload and process a document
curl -X POST "http://localhost:8000/api/v1/document-processing/process" \
  -F "file=@document.pdf" \
  -F "processing_options={\"conversion\": {\"max_pages\": 10}}"

# Check processing status
curl "http://localhost:8000/api/v1/document-processing/status/{document_id}"
```

## Pipeline Steps Detail

### Step 1: Document Conversion (Marker)

**Worker**: `DocumentConverterWorker`  
**Queue**: `document_processing:document_converter`

- Converts documents to Markdown using Marker library
- Supports multiple formats with fallback mechanisms
- Preserves document structure and formatting
- Extracts images and metadata

**Supported Formats**:
- PDF (primary via Marker)
- DOCX/DOC (python-docx fallback)
- PPTX/PPT (python-pptx fallback)
- XLSX/XLS (pandas fallback)
- EPUB (ebooklib fallback)
- HTML/HTM (html2text)
- TXT/MD (direct copy)

### Step 2: Metadata Extraction (LlamaIndex)

**Worker**: `MetadataExtractorWorker`  
**Queue**: `document_processing:metadata_extractor`

- Uses LlamaIndex extractors for structured metadata
- LLM-powered analysis for rich metadata
- Generates embeddings for important fields
- Structured output with Pydantic models

**Extracted Metadata**:
```json
{
  "title": "Document Title",
  "description": "Brief description",
  "type": "document|article|report|manual|presentation",
  "category": "Subject category",
  "authors": ["Author 1", "Author 2"],
  "date": "2024-01-15T10:30:00Z",
  "tags": ["tag1", "tag2"],
  "summary": "Document summary",
  "language": "en",
  "word_count": 1500,
  "page_count": 10
}
```

### Step 3: Typesense Indexing

**Worker**: `TypesenseIndexerWorker`  
**Queue**: `document_processing:typesense_indexer`

- Indexes metadata with full-text search capabilities
- Supports vector search with embeddings
- Faceted search on categories, types, authors
- Auto-complete and typo tolerance

**Collection Schema**:
- Full-text fields: title, description, summary
- Faceted fields: type, category, authors, tags, language
- Vector fields: title_embedding, description_embedding, summary_embedding
- Metadata fields: word_count, page_count, dates

### Step 4: Qdrant Indexing (RAG)

**Worker**: `QdrantIndexerWorker`  
**Queue**: `document_processing:qdrant_indexer`

- Creates document chunks for RAG using LlamaIndex
- Uses Typesense document ID as unique identifier
- Configurable chunking strategy (1024 chars, 200 overlap)
- OpenAI embeddings for semantic similarity

**Features**:
- Automatic chunking with overlap
- Metadata preservation in chunks
- Vector similarity search
- Integration with LlamaIndex query engines

## Configuration

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Typesense Configuration
TYPESENSE_HOST=localhost
TYPESENSE_PORT=8108
TYPESENSE_API_KEY=your_typesense_api_key

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your_qdrant_api_key  # Optional

# Processing Configuration
MAX_FILE_SIZE=50MB
UPLOAD_DIR=./uploads
PROCESSED_DIR=./processed
```

### Queue Configuration

```python
queue_names = {
    "document_converter": "document_processing:document_converter",
    "metadata_extractor": "document_processing:metadata_extractor", 
    "typesense_indexer": "document_processing:typesense_indexer",
    "qdrant_indexer": "document_processing:qdrant_indexer"
}
```

## Monitoring and Logging

### Health Checks

- `/health` - Overall system health
- `/health/redis` - Redis connection status
- `/api/v1/document-processing/health` - Pipeline-specific health

### Logging

- Structured logging with contextual information
- Job event tracking (started, completed, failed)
- Performance metrics and timing
- Error tracking with stack traces

### Job Monitoring

Each job includes:
- Progress tracking (0-100%)
- Status updates (queued, processing, completed, failed)
- Error messages and debugging info
- Processing timestamps

## Development

### Project Structure

```
app/
├── workers/                    # Background workers
│   ├── document_converter_worker.py
│   ├── metadata_extractor_worker.py
│   ├── typesense_indexer_worker.py
│   └── qdrant_indexer_worker.py
├── services/                   # Business logic
│   └── document_processing_pipeline.py
├── api/routes/                 # API endpoints
│   └── document_processing_routes.py
├── core/                       # Core configuration
│   ├── config.py
│   └── logging_config.py
└── utils/                      # Utilities
    └── exceptions.py
```

### Worker Implementation

Each worker follows the same pattern:

1. **Setup**: Initialize connections and models
2. **Process Job**: Handle job data and execute processing
3. **Progress Updates**: Report progress to job queue
4. **Error Handling**: Comprehensive error handling with retries
5. **Cleanup**: Resource cleanup and logging

### Adding New Workers

1. Create worker class inheriting from base pattern
2. Implement `process_job` method
3. Add queue configuration to `settings.queue_names`
4. Update pipeline orchestration
5. Add health checks and monitoring

## Performance Considerations

### Scalability

- **Horizontal Scaling**: Run multiple worker instances
- **Queue Management**: Configure concurrency and timeouts
- **Resource Limits**: Set memory and CPU limits for workers
- **Load Balancing**: Distribute workers across machines

### Optimization

- **Chunking Strategy**: Optimize chunk size for your use case
- **Embedding Batching**: Batch embedding generation
- **Caching**: Cache frequently accessed data
- **Connection Pooling**: Reuse database connections

### Memory Management

- **Streaming**: Process large files in chunks
- **Cleanup**: Explicit resource cleanup in workers
- **Limits**: Set file size limits and timeouts
- **Monitoring**: Track memory usage and performance

## Troubleshooting

### Common Issues

1. **Redis Connection**: Ensure Redis is running and accessible
2. **API Keys**: Verify OpenAI, Typesense, and Qdrant keys
3. **Memory**: Monitor memory usage for large documents
4. **Dependencies**: Check all required services are running

### Debugging

1. **Logs**: Check structured logs for error details
2. **Health Checks**: Use health endpoints to verify status
3. **Test Script**: Run `test_pipeline.py` for validation
4. **Queue Status**: Monitor Redis queues for stuck jobs

### Performance Issues

1. **Worker Scaling**: Increase worker instances
2. **Queue Configuration**: Adjust concurrency settings
3. **Resource Allocation**: Increase memory/CPU limits
4. **Optimization**: Profile and optimize bottlenecks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Update documentation
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **Marker**: PDF to Markdown conversion
- **LlamaIndex**: RAG framework and metadata extraction
- **Typesense**: Search engine with vector capabilities
- **Qdrant**: Vector database for similarity search
- **FastAPI**: Modern web framework for APIs
- **BullMQ**: Redis-based job queues 