#!/bin/bash

# Document Processing Workers Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment is activated
check_venv() {
    if [[ -z "$VIRTUAL_ENV" ]] && [[ -z "$CONDA_DEFAULT_ENV" ]]; then
        print_warning "No virtual environment detected. Make sure you have activated your environment."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        if [[ -n "$VIRTUAL_ENV" ]]; then
            print_status "Virtual environment detected: $(basename $VIRTUAL_ENV)"
        elif [[ -n "$CONDA_DEFAULT_ENV" ]]; then
            print_status "Conda environment detected: $CONDA_DEFAULT_ENV"
        fi
    fi
}

# Check if Redis is running
check_redis() {
    print_status "Checking Redis connection..."
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping &> /dev/null; then
            print_status "Redis is running"
        else
            print_error "Redis is not responding. Please start Redis first."
            echo "  - Using Docker: docker run -d -p 6379:6379 redis:latest"
            echo "  - Using local installation: redis-server"
            exit 1
        fi
    else
        print_warning "redis-cli not found. Cannot verify Redis connection."
    fi
}

# Function to start all workers
start_all_workers() {
    print_status "Starting all document processing workers..."
    python scripts/start_workers.py --worker all
}

# Function to start specific worker
start_worker() {
    local worker_name=$1
    print_status "Starting $worker_name worker..."
    python scripts/start_workers.py --worker "$worker_name"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  all         Start all workers (default)"
    echo "  converter   Start document converter worker only"
    echo "  typesense   Start Typesense indexer worker only"
    echo "  qdrant      Start Qdrant indexer worker only"
    echo "  sync        Start document sync worker only"
    echo "  -h, --help  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start all workers"
    echo "  $0 all               # Start all workers"
    echo "  $0 converter         # Start only converter worker"
    echo "  $0 typesense         # Start only Typesense worker"
}

# Main script
main() {
    local worker_type=${1:-all}
    
    case $worker_type in
        -h|--help)
            show_usage
            exit 0
            ;;
        all|converter|typesense|qdrant|sync)
            print_status "Document Processing Workers Startup"
            print_status "===================================="
            
            # Perform checks
            check_venv
            check_redis
            
            # Start workers
            if [[ $worker_type == "all" ]]; then
                start_all_workers
            else
                start_worker "$worker_type"
            fi
            ;;
        *)
            print_error "Unknown option: $worker_type"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'print_status "Shutting down workers..."; exit 0' INT TERM

# Run main function
main "$@" 