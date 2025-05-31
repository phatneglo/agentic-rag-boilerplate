# Document Processing API

A FastAPI-based document processing service with Redis queue management using BullMQ for background task processing.

## Features

- **Document Conversion**: Convert documents to Markdown format
- **Document Indexing**: Index documents to Typesense and Qdrant vector databases
- **Document Synchronization**: Sync documents across systems
- **Background Processing**: Asynchronous task processing with BullMQ
- **RORO Pattern**: Request-Response Object pattern implementation
- **Scalable Architecture**: Separate API and worker processes

## Architecture

```
├── app/
│   ├── api/                    # API layer
│   │   ├── routes/            # Route handlers
│   │   └── dependencies/      # FastAPI dependencies
│   ├── core/                  # Core configuration
│   │   ├── config.py         # Settings and configuration
│   │   └── logging.py        # Logging configuration
│   ├── models/               # Pydantic models
│   │   ├── requests/         # Request models
│   │   ├── responses/        # Response models
│   │   └── schemas/          # Database schemas (future)
│   ├── services/             # Business logic layer
│   │   ├── document_converter_service.py
│   │   ├── typesense_indexer_service.py
│   │   ├── qdrant_indexer_service.py
│   │   └── document_sync_service.py
│   ├── workers/              # Background workers
│   │   ├── document_converter_worker.py
│   │   ├── typesense_indexer_worker.py
│   │   ├── qdrant_indexer_worker.py
│   │   └── document_sync_worker.py
│   ├── utils/                # Utility functions
│   │   ├── queue_manager.py  # BullMQ queue management
│   │   └── exceptions.py     # Custom exceptions
│   └── main.py               # FastAPI application entry point
├── scripts/                  # Deployment and utility scripts
├── tests/                    # Test files
├── requirements.txt          # Python dependencies
├── environment.yml           # Conda environment file
├── .env.example             # Environment variables example
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Prerequisites

- Python 3.11+
- Redis 6.0+
- Node.js 18+ (for BullMQ)

## Installation

### Using Conda (Recommended)

```bash
# Create conda environment
conda env create -f environment.yml
conda activate document-processing-api

# Install BullMQ
npm install bullmq
```

### Using venv

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install BullMQ
npm install bullmq
```

## Configuration

1. Copy the environment file:
```bash
cp .env.example .env
```

2. Update the `.env` file with your configuration:
```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
LOG_LEVEL=INFO

# Queue Configuration
QUEUE_PREFIX=document_processing
MAX_RETRIES=3
JOB_TIMEOUT=300

# External Services
TYPESENSE_HOST=localhost
TYPESENSE_PORT=8108
TYPESENSE_API_KEY=your_api_key

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your_api_key
```

## Running the Application

### Start Redis
```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or using local Redis installation
redis-server
```

### Start the API Server
```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Start the Workers
```bash
# Start all workers (in separate terminals)
python -m app.workers.document_converter_worker
python -m app.workers.typesense_indexer_worker
python -m app.workers.qdrant_indexer_worker
python -m app.workers.document_sync_worker
```

## API Endpoints

### Document Conversion
```http
POST /api/v1/documents/convert
Content-Type: application/json

{
  "document_id": "doc_123",
  "source_path": "/path/to/document.pdf",
  "output_path": "/path/to/output.md",
  "conversion_options": {
    "preserve_formatting": true,
    "extract_images": false
  }
}
```

### Typesense Indexing
```http
POST /api/v1/documents/index/typesense
Content-Type: application/json

{
  "document_id": "doc_123",
  "content": "Document content to index",
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "tags": ["tag1", "tag2"]
  },
  "collection_name": "documents"
}
```

### Qdrant Indexing
```http
POST /api/v1/documents/index/qdrant
Content-Type: application/json

{
  "document_id": "doc_123",
  "content": "Document content to vectorize",
  "metadata": {
    "title": "Document Title",
    "source": "upload"
  },
  "collection_name": "document_vectors"
}
```

### Document Synchronization
```http
POST /api/v1/documents/sync
Content-Type: application/json

{
  "source_document_id": "doc_123",
  "target_systems": ["typesense", "qdrant"],
  "sync_options": {
    "force_update": false,
    "batch_size": 100
  }
}
```

## Development

### Code Style
This project follows:
- **PEP 8** for Python code style
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking

```bash
# Format code
black app/
isort app/

# Type checking
mypy app/

# Linting
flake8 app/
```

### Testing
```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_document_converter_service.py
```

### Adding New Services

1. Create service in `app/services/`
2. Create corresponding worker in `app/workers/`
3. Add request/response models in `app/models/`
4. Create route in `app/api/routes/`
5. Add tests in `tests/`

## Monitoring

### Queue Monitoring
The application includes built-in queue monitoring endpoints:

```http
GET /api/v1/queues/status
GET /api/v1/queues/{queue_name}/jobs
GET /api/v1/queues/{queue_name}/stats
```

### Health Checks
```http
GET /health
GET /health/redis
```

## Deployment

### Docker
```bash
# Build image
docker build -t document-processing-api .

# Run container
docker run -p 8000:8000 document-processing-api
```

### Production Considerations
- Use a process manager like **Supervisor** or **systemd** for workers
- Set up **Redis Cluster** for high availability
- Use **nginx** as a reverse proxy
- Implement proper logging and monitoring
- Set up **Redis persistence** for job durability

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details. 