#!/usr/bin/env python3
"""
Setup and Test Script for Document Processing API
This script helps you set up and test the entire system.
"""
import asyncio
import subprocess
import sys
import time
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class SetupManager:
    """Manages the setup and testing of the Document Processing API."""
    
    def __init__(self):
        self.processes = []
        
    def check_requirements(self):
        """Check if all requirements are met."""
        console.print(Panel.fit("🔍 Checking Requirements", style="bold blue"))
        
        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 10):
            console.print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}", style="green")
        else:
            console.print(f"❌ Python {python_version.major}.{python_version.minor}.{python_version.micro} (requires 3.10+)", style="red")
            return False
        
        # Check if Redis is running
        try:
            result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and "PONG" in result.stdout:
                console.print("✅ Redis is running", style="green")
            else:
                console.print("❌ Redis is not responding", style="red")
                console.print("💡 Start Redis with: docker run -d -p 6379:6379 redis:latest", style="blue")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            console.print("❌ Redis CLI not found or not responding", style="red")
            console.print("💡 Start Redis with: docker run -d -p 6379:6379 redis:latest", style="blue")
            return False
        
        # Check if .env file exists
        if Path(".env").exists():
            console.print("✅ .env file exists", style="green")
        else:
            console.print("⚠️ .env file not found", style="yellow")
            console.print("💡 Creating .env from template...", style="blue")
            try:
                if Path(".env.example").exists():
                    import shutil
                    shutil.copy(".env.example", ".env")
                    console.print("✅ .env file created from template", style="green")
                else:
                    console.print("❌ .env.example not found", style="red")
                    return False
            except Exception as e:
                console.print(f"❌ Failed to create .env: {e}", style="red")
                return False
        
        return True
    
    def start_api_server(self):
        """Start the FastAPI server."""
        console.print("🚀 Starting FastAPI server...", style="blue")
        
        try:
            # Start the API server
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--reload", 
                "--host", "0.0.0.0", 
                "--port", "8000"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(("API Server", process))
            
            # Wait a bit for the server to start
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                console.print("✅ FastAPI server started on http://localhost:8000", style="green")
                return True
            else:
                stdout, stderr = process.communicate()
                console.print(f"❌ FastAPI server failed to start", style="red")
                console.print(f"Error: {stderr.decode()}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Failed to start API server: {e}", style="red")
            return False
    
    def start_workers(self):
        """Start the background workers."""
        console.print("⚡ Starting background workers...", style="blue")
        
        try:
            # Start workers using the Python script
            process = subprocess.Popen([
                sys.executable, "scripts/start_workers.py", "--worker", "all"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(("Workers", process))
            
            # Wait a bit for workers to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                console.print("✅ Background workers started", style="green")
                return True
            else:
                stdout, stderr = process.communicate()
                console.print(f"❌ Workers failed to start", style="red")
                console.print(f"Error: {stderr.decode()}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Failed to start workers: {e}", style="red")
            return False
    
    async def run_tests(self):
        """Run the system tests."""
        console.print("🧪 Running system tests...", style="blue")
        
        # Wait a bit more for everything to be ready
        await asyncio.sleep(2)
        
        try:
            # Import and run the test system
            from test_system import SystemTester
            
            tester = SystemTester()
            await tester.run_all_tests()
            
        except Exception as e:
            console.print(f"❌ Tests failed: {e}", style="red")
            return False
        
        return True
    
    def cleanup(self):
        """Clean up running processes."""
        console.print("\n🧹 Cleaning up...", style="yellow")
        
        for name, process in self.processes:
            if process.poll() is None:
                console.print(f"Stopping {name}...", style="yellow")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        
        console.print("✅ Cleanup complete", style="green")
    
    async def run_full_setup_and_test(self):
        """Run the complete setup and test process."""
        try:
            console.print(Panel.fit("🚀 Document Processing API - Setup & Test", style="bold blue"))
            
            # Check requirements
            if not self.check_requirements():
                console.print("❌ Requirements check failed. Please fix the issues above.", style="red")
                return False
            
            # Start API server
            if not self.start_api_server():
                console.print("❌ Failed to start API server.", style="red")
                return False
            
            # Start workers
            if not self.start_workers():
                console.print("❌ Failed to start workers.", style="red")
                return False
            
            # Run tests
            console.print("\n" + "="*60, style="blue")
            console.print("🎯 System is running! Starting tests...", style="bold green")
            console.print("="*60, style="blue")
            
            await self.run_tests()
            
            # Keep running for a bit to show results
            console.print("\n" + "="*60, style="blue")
            console.print("✨ Setup and test complete!", style="bold green")
            console.print("📖 API Documentation: http://localhost:8000/docs", style="blue")
            console.print("🔍 Health Check: http://localhost:8000/health", style="blue")
            console.print("="*60, style="blue")
            
            console.print("\n⏳ Keeping services running for 30 seconds...", style="yellow")
            console.print("Press Ctrl+C to stop early", style="dim")
            
            try:
                await asyncio.sleep(30)
            except KeyboardInterrupt:
                console.print("\n⚠️ Interrupted by user", style="yellow")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Setup failed: {e}", style="red")
            return False
        finally:
            self.cleanup()


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup and test Document Processing API")
    parser.add_argument("--test-only", action="store_true", help="Run tests only (assumes services are running)")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't cleanup processes after testing")
    
    args = parser.parse_args()
    
    setup_manager = SetupManager()
    
    if args.test_only:
        # Just run tests
        console.print(Panel.fit("🧪 Running Tests Only", style="bold blue"))
        await setup_manager.run_tests()
    else:
        # Full setup and test
        success = await setup_manager.run_full_setup_and_test()
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n⚠️ Setup interrupted by user", style="yellow")
    except Exception as e:
        console.print(f"\n❌ Setup failed with error: {e}", style="red")
        sys.exit(1) 