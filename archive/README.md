# Agentic RAG - Archive Directory

This directory contains all the development, testing, and debugging files that were created during the implementation of the 4-step document processing pipeline. These files have been moved here to keep the root directory clean and production-ready.

## 📁 Directory Structure

### `/tests/` - Test Scripts
Development and testing scripts for various pipeline components:

- `test_real_pdf_pipeline.py` - Complete pipeline test with real PDF files
- `test_full_pdf_pipeline.py` - Full end-to-end pipeline testing
- `test_complete_pipeline.py` - Complete system testing
- `test_persistent_pipeline.py` - Pipeline persistence testing
- `test_html_file_pipeline.py` - HTML file processing tests
- `test_worker_demo.py` - Worker demonstration scripts
- `test_pipeline.py` - Basic pipeline testing
- `test_*_qdrant*.py` - Various Qdrant integration tests
- `test_websocket_client.py` - WebSocket functionality tests
- `test_*streaming*.py` - Streaming and real-time feature tests
- `demo_*.py` - Demonstration scripts for agents and chat
- `test_system.py` - Comprehensive system testing

### `/debug/` - Debug & Setup Scripts
Debugging, troubleshooting, and setup utilities:

- `debug_*.py` - Various debugging scripts for pipeline issues
- `recreate_*.py` - Collection recreation scripts for Qdrant/Typesense
- `setup_*.py` - Setup and initialization scripts
- `check_*.py` - Status checking and verification scripts
- `converted_*.md` - Sample converted documents
- `test_complete_fixes.html` - HTML test files
- `environment.yml` - Conda environment specification

### `/docs/` - Additional Documentation
Extra documentation files created during development:

- `README_PIPELINE.md` - Detailed pipeline documentation
- `README_AGENTS.md` - Agent system documentation
- `CLAUDE_STREAMING_IMPROVEMENTS.md` - Streaming improvements notes
- `FILE_MANAGER_README.md` - File manager documentation
- `env.example` - Environment configuration example

## 🔧 Usage

These archived files are maintained for:

1. **Reference**: Understanding how the pipeline was developed and tested
2. **Debugging**: Troubleshooting pipeline issues using proven test scripts
3. **Development**: Extending or modifying pipeline components
4. **Testing**: Running comprehensive tests during updates

## 🚀 Running Archived Tests

To run any archived test script:

```bash
# Copy test script to root directory
cp archive/tests/test_real_pdf_pipeline.py .

# Activate virtual environment
source venv/bin/activate

# Run the test
python test_real_pdf_pipeline.py

# Clean up after testing
rm test_real_pdf_pipeline.py
```

## 📝 Development History

This archive represents the complete development journey of implementing:

1. **Document Conversion Pipeline** - PDF/DOCX/TXT/HTML to Markdown
2. **Metadata Extraction** - AI-powered content analysis with LlamaIndex
3. **Search Indexing** - Typesense integration with auto-embedding
4. **RAG Integration** - Qdrant vector storage with LlamaIndex
5. **Queue Management** - BullMQ with Redis for background processing
6. **Worker System** - 4-step parallel processing workers
7. **Real-time Chat** - WebSocket-based chat with RAG capabilities
8. **System Integration** - Complete end-to-end document processing

## 🧹 Keeping Clean

The main project directory now contains only:
- Production code (`app/`, `static/`)
- Startup scripts (`start_*.sh`)
- Core documentation (`README.md`)
- Configuration files (`.env`, `requirements.txt`)
- Development infrastructure (`venv/`, `logs/`, etc.)

This archive ensures all development work is preserved while maintaining a clean, professional project structure. 