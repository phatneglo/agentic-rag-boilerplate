#!/bin/bash

echo "🛑 Stopping All Agentic RAG Processes"
echo "====================================="
echo ""

# Function to try killing processes with different methods
kill_processes() {
    local pattern="$1"
    local description="$2"
    
    echo "🔍 Looking for $description..."
    
    # Find matching processes
    PIDS=$(ps aux | grep -E "$pattern" | grep -v grep | awk '{print $2}')
    
    if [ -z "$PIDS" ]; then
        echo "   ✅ No $description found"
        return 0
    fi
    
    echo "   Found processes: $PIDS"
    
    # Try graceful kill first
    for pid in $PIDS; do
        echo "   Stopping PID $pid..."
        kill $pid 2>/dev/null && echo "     ✅ Gracefully stopped" || echo "     ⚠️  Could not stop (may need sudo)"
    done
    
    # Wait a moment
    sleep 2
    
    # Check if any are still running
    REMAINING=$(ps aux | grep -E "$pattern" | grep -v grep | awk '{print $2}')
    if [ ! -z "$REMAINING" ]; then
        echo "   ⚠️  Some processes still running: $REMAINING"
        echo "   To force kill: sudo kill -9 $REMAINING"
        return 1
    else
        echo "   ✅ All $description stopped"
        return 0
    fi
}

# Stop FastAPI server
kill_processes "uvicorn.*app.main" "FastAPI servers"

# Stop workers
kill_processes "app.workers.simple_document_converter_worker" "Document Converter workers"
kill_processes "app.workers.metadata_extractor_worker" "Metadata Extractor workers"
kill_processes "app.workers.typesense_indexer_worker" "Typesense Indexer workers"
kill_processes "app.workers.qdrant_indexer_worker" "Qdrant Indexer workers"

# Check for any remaining worker processes
echo ""
echo "🔍 Final check for any remaining processes..."
REMAINING_ALL=$(ps aux | grep -E "(app.workers|uvicorn.*app.main)" | grep -v grep)

if [ -z "$REMAINING_ALL" ]; then
    echo "✅ All Agentic RAG processes have been stopped!"
else
    echo "⚠️  Some processes are still running:"
    echo "$REMAINING_ALL"
    echo ""
    echo "To force kill all remaining processes:"
    echo "sudo pkill -f 'app.workers'"
    echo "sudo pkill -f 'uvicorn.*app.main'"
fi

echo ""
echo "💡 Tips:"
echo "   • If processes won't stop, try: sudo ./stop_all.sh"
echo "   • To avoid conflicts, wait 5 seconds before restarting"
echo "   • Use ./start_server_and_workers.sh to restart" 