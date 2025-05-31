#!/usr/bin/env python3
"""
System Integration Test Script
Tests the complete Document Processing API system including:
- API endpoints
- Redis connectivity
- Queue functionality
- Worker processing
"""
import asyncio
import json
import time
import sys
from typing import Dict, Any, List
import httpx
import redis.asyncio as redis
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live

console = Console()

class SystemTester:
    """Comprehensive system tester for the Document Processing API."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000", redis_url: str = "redis://localhost:6379/0"):
        self.api_base_url = api_base_url
        self.redis_url = redis_url
        self.test_results = []
        self.redis_client = None
        
    async def setup(self):
        """Setup test environment."""
        console.print(Panel.fit("🚀 Document Processing API - System Test", style="bold blue"))
        
        # Setup Redis client
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            console.print("✅ Redis connection established", style="green")
        except Exception as e:
            console.print(f"❌ Redis connection failed: {e}", style="red")
            return False
        
        return True
    
    async def cleanup(self):
        """Cleanup test environment."""
        if self.redis_client:
            await self.redis_client.close()
    
    def add_test_result(self, test_name: str, success: bool, details: str = "", duration: float = 0):
        """Add test result."""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "duration": duration
        })
    
    async def test_api_health(self) -> bool:
        """Test API health endpoints."""
        console.print("\n📊 Testing API Health...", style="bold yellow")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test general health
                start_time = time.time()
                response = await client.get(f"{self.api_base_url}/health")
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    console.print(f"✅ General health check: {data.get('status', 'unknown')}", style="green")
                    self.add_test_result("API Health Check", True, f"Status: {data.get('status')}", duration)
                else:
                    console.print(f"❌ Health check failed: {response.status_code}", style="red")
                    self.add_test_result("API Health Check", False, f"HTTP {response.status_code}", duration)
                    return False
                
                # Test Redis health
                start_time = time.time()
                response = await client.get(f"{self.api_base_url}/health/redis")
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    console.print(f"✅ Redis health check: {data.get('status', 'unknown')}", style="green")
                    self.add_test_result("Redis Health Check", True, f"Status: {data.get('status')}", duration)
                else:
                    console.print(f"❌ Redis health check failed: {response.status_code}", style="red")
                    self.add_test_result("Redis Health Check", False, f"HTTP {response.status_code}", duration)
                    return False
                
                return True
                
        except Exception as e:
            console.print(f"❌ API health test failed: {e}", style="red")
            self.add_test_result("API Health Check", False, str(e))
            return False
    
    async def test_document_conversion(self) -> Dict[str, Any]:
        """Test document conversion endpoint."""
        console.print("\n📄 Testing Document Conversion...", style="bold yellow")
        
        test_data = {
            "document_id": "test_doc_001",
            "source_path": "/tmp/test_document.pdf",
            "output_path": "/tmp/test_document.md",
            "conversion_options": {
                "preserve_formatting": True,
                "extract_images": False
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.api_base_url}/api/v1/documents/convert",
                    json=test_data,
                    timeout=30.0
                )
                duration = time.time() - start_time
                
                if response.status_code == 201:
                    data = response.json()
                    job_id = data.get("job_id")
                    console.print(f"✅ Document conversion job created: {job_id}", style="green")
                    self.add_test_result("Document Conversion", True, f"Job ID: {job_id}", duration)
                    return data
                else:
                    console.print(f"❌ Document conversion failed: {response.status_code}", style="red")
                    console.print(f"Response: {response.text}", style="red")
                    self.add_test_result("Document Conversion", False, f"HTTP {response.status_code}", duration)
                    return {}
                    
        except Exception as e:
            console.print(f"❌ Document conversion test failed: {e}", style="red")
            self.add_test_result("Document Conversion", False, str(e))
            return {}
    
    async def test_typesense_indexing(self) -> Dict[str, Any]:
        """Test Typesense indexing endpoint."""
        console.print("\n🔍 Testing Typesense Indexing...", style="bold yellow")
        
        test_data = {
            "document_id": "test_doc_002",
            "content": "This is a test document for Typesense indexing. It contains sample content to verify the indexing functionality.",
            "metadata": {
                "title": "Test Document",
                "author": "System Tester",
                "tags": ["test", "indexing", "typesense"]
            },
            "collection_name": "test_documents"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.api_base_url}/api/v1/documents/index/typesense",
                    json=test_data,
                    timeout=30.0
                )
                duration = time.time() - start_time
                
                if response.status_code == 201:
                    data = response.json()
                    job_id = data.get("job_id")
                    console.print(f"✅ Typesense indexing job created: {job_id}", style="green")
                    self.add_test_result("Typesense Indexing", True, f"Job ID: {job_id}", duration)
                    return data
                else:
                    console.print(f"❌ Typesense indexing failed: {response.status_code}", style="red")
                    console.print(f"Response: {response.text}", style="red")
                    self.add_test_result("Typesense Indexing", False, f"HTTP {response.status_code}", duration)
                    return {}
                    
        except Exception as e:
            console.print(f"❌ Typesense indexing test failed: {e}", style="red")
            self.add_test_result("Typesense Indexing", False, str(e))
            return {}
    
    async def test_qdrant_indexing(self) -> Dict[str, Any]:
        """Test Qdrant indexing endpoint."""
        console.print("\n🎯 Testing Qdrant Indexing...", style="bold yellow")
        
        test_data = {
            "document_id": "test_doc_003",
            "content": "This is a test document for Qdrant vector indexing. It will be converted to embeddings and stored in the vector database.",
            "metadata": {
                "title": "Vector Test Document",
                "source": "system_test"
            },
            "collection_name": "test_vectors"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.api_base_url}/api/v1/documents/index/qdrant",
                    json=test_data,
                    timeout=30.0
                )
                duration = time.time() - start_time
                
                if response.status_code == 201:
                    data = response.json()
                    job_id = data.get("job_id")
                    console.print(f"✅ Qdrant indexing job created: {job_id}", style="green")
                    self.add_test_result("Qdrant Indexing", True, f"Job ID: {job_id}", duration)
                    return data
                else:
                    console.print(f"❌ Qdrant indexing failed: {response.status_code}", style="red")
                    console.print(f"Response: {response.text}", style="red")
                    self.add_test_result("Qdrant Indexing", False, f"HTTP {response.status_code}", duration)
                    return {}
                    
        except Exception as e:
            console.print(f"❌ Qdrant indexing test failed: {e}", style="red")
            self.add_test_result("Qdrant Indexing", False, str(e))
            return {}
    
    async def test_document_sync(self) -> Dict[str, Any]:
        """Test document synchronization endpoint."""
        console.print("\n🔄 Testing Document Synchronization...", style="bold yellow")
        
        test_data = {
            "source_document_id": "test_doc_004",
            "target_systems": ["typesense", "qdrant"],
            "sync_options": {
                "force_update": False,
                "batch_size": 10
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.api_base_url}/api/v1/documents/sync",
                    json=test_data,
                    timeout=30.0
                )
                duration = time.time() - start_time
                
                if response.status_code == 201:
                    data = response.json()
                    job_id = data.get("job_id")
                    console.print(f"✅ Document sync job created: {job_id}", style="green")
                    self.add_test_result("Document Synchronization", True, f"Job ID: {job_id}", duration)
                    return data
                else:
                    console.print(f"❌ Document sync failed: {response.status_code}", style="red")
                    console.print(f"Response: {response.text}", style="red")
                    self.add_test_result("Document Synchronization", False, f"HTTP {response.status_code}", duration)
                    return {}
                    
        except Exception as e:
            console.print(f"❌ Document sync test failed: {e}", style="red")
            self.add_test_result("Document Synchronization", False, str(e))
            return {}
    
    async def test_queue_functionality(self, job_ids: List[str]):
        """Test queue functionality by checking job status."""
        console.print("\n⚡ Testing Queue Functionality...", style="bold yellow")
        
        if not job_ids:
            console.print("⚠️ No job IDs to test queue functionality", style="yellow")
            return
        
        # Wait a bit for jobs to be processed
        console.print("⏳ Waiting for jobs to be processed...", style="blue")
        await asyncio.sleep(3)
        
        # Check Redis for queue data
        try:
            queue_names = [
                "document_processing:document_converter",
                "document_processing:typesense_indexer",
                "document_processing:qdrant_indexer",
                "document_processing:document_sync"
            ]
            
            for queue_name in queue_names:
                # Check if queue exists in Redis
                exists = await self.redis_client.exists(f"bull:{queue_name}:meta")
                if exists:
                    console.print(f"✅ Queue exists: {queue_name}", style="green")
                    self.add_test_result(f"Queue Exists: {queue_name}", True, "Queue found in Redis")
                else:
                    console.print(f"⚠️ Queue not found: {queue_name}", style="yellow")
                    self.add_test_result(f"Queue Exists: {queue_name}", False, "Queue not found in Redis")
            
        except Exception as e:
            console.print(f"❌ Queue functionality test failed: {e}", style="red")
            self.add_test_result("Queue Functionality", False, str(e))
    
    async def test_api_documentation(self):
        """Test API documentation endpoints."""
        console.print("\n📚 Testing API Documentation...", style="bold yellow")
        
        endpoints = [
            ("/docs", "Swagger UI"),
            ("/redoc", "ReDoc"),
            ("/openapi.json", "OpenAPI Schema"),
            ("/", "Root endpoint")
        ]
        
        try:
            async with httpx.AsyncClient() as client:
                for endpoint, name in endpoints:
                    start_time = time.time()
                    response = await client.get(f"{self.api_base_url}{endpoint}")
                    duration = time.time() - start_time
                    
                    if response.status_code == 200:
                        console.print(f"✅ {name}: Available", style="green")
                        self.add_test_result(f"Documentation: {name}", True, "Available", duration)
                    else:
                        console.print(f"❌ {name}: Failed ({response.status_code})", style="red")
                        self.add_test_result(f"Documentation: {name}", False, f"HTTP {response.status_code}", duration)
                        
        except Exception as e:
            console.print(f"❌ Documentation test failed: {e}", style="red")
            self.add_test_result("API Documentation", False, str(e))
    
    def display_results(self):
        """Display test results in a nice table."""
        console.print("\n📊 Test Results Summary", style="bold blue")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Details", style="dim")
        
        passed = 0
        failed = 0
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            status_style = "green" if result["success"] else "red"
            duration = f"{result['duration']:.3f}s" if result['duration'] > 0 else "-"
            
            table.add_row(
                result["test"],
                f"[{status_style}]{status}[/{status_style}]",
                duration,
                result["details"]
            )
            
            if result["success"]:
                passed += 1
            else:
                failed += 1
        
        console.print(table)
        
        # Summary
        total = passed + failed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        summary_style = "green" if failed == 0 else "yellow" if success_rate >= 70 else "red"
        console.print(f"\n[{summary_style}]Summary: {passed}/{total} tests passed ({success_rate:.1f}%)[/{summary_style}]")
        
        if failed == 0:
            console.print("🎉 All tests passed! Your system is working correctly.", style="bold green")
        elif success_rate >= 70:
            console.print("⚠️ Most tests passed, but some issues detected.", style="bold yellow")
        else:
            console.print("❌ Multiple test failures detected. Please check your setup.", style="bold red")
    
    async def run_all_tests(self):
        """Run all system tests."""
        if not await self.setup():
            console.print("❌ Setup failed. Cannot continue with tests.", style="red")
            return
        
        try:
            job_ids = []
            
            # Test API health
            if not await self.test_api_health():
                console.print("❌ API health tests failed. Skipping endpoint tests.", style="red")
                return
            
            # Test all endpoints
            conversion_result = await self.test_document_conversion()
            if conversion_result.get("job_id"):
                job_ids.append(conversion_result["job_id"])
            
            typesense_result = await self.test_typesense_indexing()
            if typesense_result.get("job_id"):
                job_ids.append(typesense_result["job_id"])
            
            qdrant_result = await self.test_qdrant_indexing()
            if qdrant_result.get("job_id"):
                job_ids.append(qdrant_result["job_id"])
            
            sync_result = await self.test_document_sync()
            if sync_result.get("job_id"):
                job_ids.append(sync_result["job_id"])
            
            # Test queue functionality
            await self.test_queue_functionality(job_ids)
            
            # Test documentation
            await self.test_api_documentation()
            
            # Display results
            self.display_results()
            
        finally:
            await self.cleanup()


async def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Document Processing API system")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--redis-url", default="redis://localhost:6379/0", help="Redis URL")
    
    args = parser.parse_args()
    
    tester = SystemTester(api_base_url=args.api_url, redis_url=args.redis_url)
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n⚠️ Test interrupted by user", style="yellow")
    except Exception as e:
        console.print(f"\n❌ Test failed with error: {e}", style="red")
        sys.exit(1) 