#!/usr/bin/env python3
"""
Verification script to test that all major dependencies are properly installed and working.
"""

import sys
import importlib
import traceback
from typing import List, Tuple

def test_import(module_name: str, description: str = "") -> Tuple[bool, str]:
    """Test importing a module and return success status and message."""
    try:
        importlib.import_module(module_name)
        return True, f"✅ {module_name} - {description or 'OK'}"
    except ImportError as e:
        return False, f"❌ {module_name} - {description or 'Failed'}: {e}"
    except Exception as e:
        return False, f"⚠️  {module_name} - {description or 'Error'}: {e}"

def test_specific_functionality():
    """Test specific functionality of key packages."""
    results = []
    
    # Test FastAPI
    try:
        from fastapi import FastAPI
        app = FastAPI()
        results.append((True, "✅ FastAPI - Can create app instance"))
    except Exception as e:
        results.append((False, f"❌ FastAPI - Cannot create app: {e}"))
    
    # Test Pydantic
    try:
        from pydantic import BaseModel
        class TestModel(BaseModel):
            name: str = "test"
        model = TestModel()
        results.append((True, "✅ Pydantic - Can create model"))
    except Exception as e:
        results.append((False, f"❌ Pydantic - Cannot create model: {e}"))
    
    # Test OpenAI client
    try:
        from openai import OpenAI
        # Don't actually call API, just test instantiation
        client = OpenAI(api_key="dummy-key")
        results.append((True, "✅ OpenAI - Can create client"))
    except Exception as e:
        results.append((False, f"❌ OpenAI - Cannot create client: {e}"))
    
    # Test LangChain
    try:
        from langchain.schema import Document
        doc = Document(page_content="test", metadata={})
        results.append((True, "✅ LangChain - Can create document"))
    except Exception as e:
        results.append((False, f"❌ LangChain - Cannot create document: {e}"))
    
    # Test LlamaIndex
    try:
        from llama_index.core import Document as LlamaDocument
        doc = LlamaDocument(text="test")
        results.append((True, "✅ LlamaIndex - Can create document"))
    except Exception as e:
        results.append((False, f"❌ LlamaIndex - Cannot create document: {e}"))
    
    # Test Qdrant client
    try:
        from qdrant_client import QdrantClient
        # Don't actually connect, just test instantiation
        client = QdrantClient(":memory:")
        results.append((True, "✅ Qdrant - Can create in-memory client"))
    except Exception as e:
        results.append((False, f"❌ Qdrant - Cannot create client: {e}"))
    
    # Test Redis
    try:
        import redis
        # Don't actually connect, just test import
        results.append((True, "✅ Redis - Module imported"))
    except Exception as e:
        results.append((False, f"❌ Redis - Cannot import: {e}"))
    
    return results

def main():
    """Main verification function."""
    print("🔍 Verifying Python environment and dependencies...")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print("=" * 60)
    
    # Core Python packages
    core_packages = [
        ("fastapi", "Web framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("redis", "Redis client"),
        ("httpx", "HTTP client"),
        ("dotenv", "Environment variables (python-dotenv)"),
    ]
    
    # AI/ML packages
    ai_packages = [
        ("openai", "OpenAI API client"),
        ("langchain", "LangChain framework"),
        ("langchain_openai", "LangChain OpenAI integration"),
        ("langgraph", "LangGraph"),
        ("llama_index", "LlamaIndex"),
        ("llama_index.core", "LlamaIndex core"),
        ("llama_index.embeddings.openai", "LlamaIndex OpenAI embeddings"),
    ]
    
    # Document processing packages
    doc_packages = [
        ("qdrant_client", "Vector database client"),
        ("magic", "File type detection (python-magic-bin)"),
        ("marker", "PDF processing"),
        ("pypdf", "PDF parsing"),
        ("pandas", "Data manipulation"),
        ("numpy", "Numerical computing"),
    ]
    
    # Development packages
    dev_packages = [
        ("structlog", "Structured logging"),
        ("rich", "Rich text and beautiful formatting"),
        ("pytest", "Testing framework"),
        ("black", "Code formatter"),
        ("mypy", "Type checker"),
    ]
    
    all_results = []
    
    print("\n📦 Core Packages:")
    for package, desc in core_packages:
        success, message = test_import(package, desc)
        all_results.append((success, message))
        print(f"  {message}")
    
    print("\n🤖 AI/ML Packages:")
    for package, desc in ai_packages:
        success, message = test_import(package, desc)
        all_results.append((success, message))
        print(f"  {message}")
    
    print("\n📄 Document Processing Packages:")
    for package, desc in doc_packages:
        success, message = test_import(package, desc)
        all_results.append((success, message))
        print(f"  {message}")
    
    print("\n🛠️  Development Packages:")
    for package, desc in dev_packages:
        success, message = test_import(package, desc)
        all_results.append((success, message))
        print(f"  {message}")
    
    print("\n🔧 Functionality Tests:")
    func_results = test_specific_functionality()
    all_results.extend(func_results)
    for success, message in func_results:
        print(f"  {message}")
    
    print("\n" + "=" * 60)
    
    # Summary
    total_tests = len(all_results)
    passed_tests = sum(1 for success, _ in all_results if success)
    failed_tests = total_tests - passed_tests
    
    print(f"📊 Summary: {passed_tests}/{total_tests} tests passed")
    
    if failed_tests > 0:
        print(f"❌ {failed_tests} tests failed")
        print("\nFailed tests:")
        for success, message in all_results:
            if not success:
                print(f"  {message}")
        sys.exit(1)
    else:
        print("✅ All tests passed! Your environment is ready.")
        return True

if __name__ == "__main__":
    main() 