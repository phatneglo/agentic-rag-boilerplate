# Windows Setup Guide for Agentic RAG Boilerplate

This guide will help you set up the Agentic RAG Boilerplate application on Windows using conda.

## Prerequisites

- **Anaconda or Miniconda** installed on your Windows system
- **Python 3.12.7 or higher** (handled by conda)
- **Git** for version control

## Quick Setup

### 1. Activate the Conda Environment

The environment `agentic-rag` has already been set up for you with Python 3.12.10 and all required dependencies.

```powershell
conda activate agentic-rag
```

### 2. Verify Installation

Run the verification script to ensure all packages are working correctly:

```powershell
python verify_installation.py
```

You should see all tests passing (31/31).

### 3. Environment Configuration

Create a `.env` file in the project root with your configuration:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Redis Configuration (if using external Redis)
REDIS_URL=redis://localhost:6379

# Qdrant Configuration (if using external Qdrant)
QDRANT_URL=http://localhost:6333

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO
```

## Installed Packages

### Core Dependencies
- **FastAPI 0.115.6** - Web framework
- **Uvicorn 0.32.1** - ASGI server
- **Pydantic 2.10.4** - Data validation
- **Redis 5.2.1** - Redis client
- **python-dotenv 1.0.1** - Environment variables

### AI/ML Dependencies
- **OpenAI 1.82.1** - OpenAI API client
- **LangChain 0.3.25** - LangChain framework with OpenAI integration
- **LangGraph 0.3.28** - Multi-agent workflows
- **LlamaIndex 0.12.39** - Document indexing and retrieval
- **LlamaIndex OpenAI integrations** - Embeddings and LLMs

### Document Processing
- **qdrant-client 1.12.1** - Vector database client
- **python-magic-bin 0.4.14** - File type detection (Windows-compatible)
- **marker-pdf 1.7.3** - Advanced PDF processing
- **pandas 2.2.3** - Data manipulation
- **pypdf 5.6.0** - PDF parsing

### Development Tools
- **pytest 8.3.4** - Testing framework
- **black 24.10.0** - Code formatter
- **mypy 1.16.0** - Type checker
- **structlog 25.3.0** - Structured logging
- **rich 13.9.4** - Beautiful terminal output

## Windows-Specific Considerations

### 1. File Magic Detection
We use `python-magic-bin` instead of `python-magic` as it includes the required Windows binaries.

### 2. UV Loop
`uvloop` is not supported on Windows and has been excluded from the installation.

### 3. Path Separators
The application handles Windows path separators automatically.

## Running the Application

### Start the Server

```powershell
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the start script (if available)
.\start_server_and_workers.bat
```

### Start Background Workers

If your application uses background workers (BullMQ/Redis):

```powershell
# Make sure Redis is running
# Then start workers as needed
```

## Testing

Run the test suite:

```powershell
pytest
```

Run specific tests:

```powershell
pytest tests/test_specific_module.py
```

## Development

### Code Formatting
```powershell
black app/
```

### Type Checking
```powershell
mypy app/
```

### Linting
```powershell
flake8 app/
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're in the correct conda environment:
   ```powershell
   conda activate agentic-rag
   ```

2. **Redis Connection Issues**: 
   - Install Redis for Windows or use WSL
   - Update Redis connection string in `.env`

3. **PDF Processing Issues**:
   - Ensure `marker-pdf` dependencies are properly installed
   - Check if additional system libraries are needed

4. **Memory Issues with Large Documents**:
   - Monitor memory usage during document processing
   - Consider processing documents in smaller chunks

### Getting Help

1. Check the verification script output for missing dependencies
2. Review the application logs for specific error messages
3. Ensure all environment variables are properly configured

## Package Versions

For a complete list of installed packages and their versions, run:

```powershell
pip list
```

Or check the `windows_requirements.txt` file for the specific versions used in this setup.

## Next Steps

1. Configure your API keys in the `.env` file
2. Set up Redis and Qdrant if using external instances
3. Test document upload and processing functionality
4. Explore the API documentation at `http://localhost:8000/docs` when the server is running

## Environment Recreation

If you need to recreate this environment:

1. Create a new conda environment:
   ```powershell
   conda create -n agentic-rag-new python=3.12.7
   conda activate agentic-rag-new
   ```

2. Install dependencies:
   ```powershell
   pip install -r windows_requirements.txt
   ```

3. Verify installation:
   ```powershell
   python verify_installation.py
   ```

Your Windows development environment is now ready for the Agentic RAG Boilerplate! 🚀 