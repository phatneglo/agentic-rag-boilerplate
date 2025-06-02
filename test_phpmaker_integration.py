#!/usr/bin/env python3
"""
Test PHPMaker Integration

This script demonstrates the complete PHPMaker authentication flow:
1. Login with user credentials -> Get JWT and session
2. Use session to make authenticated API requests
3. Handle session management

Setup:
1. Set environment variables:
   - PHPMAKER_API_URL=https://your-phpmaker-app.com/api
2. Update this script with actual user credentials
3. Run the test
"""

import asyncio
import aiohttp
import json
import sys
import os

# Add the parent directory to the Python path  
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


class PHPMakerIntegrationTest:
    """Test class for PHPMaker integration."""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.session = None
        self.session_id = None
        self.user_info = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_connection(self):
        """Test connection to PHPMaker API through our service."""
        print("🔗 Testing PHPMaker API connection...")
        
        try:
            async with self.session.get(f"{self.api_base_url}/api/v1/phpmaker-auth/test-connection") as response:
                result = await response.json()
                
                if result.get('success'):
                    print(f"✅ Connection successful to: {result.get('api_url')}")
                    return True
                else:
                    print(f"❌ Connection failed: {result.get('message')}")
                    return False
                    
        except Exception as e:
            print(f"❌ Connection test error: {e}")
            return False
    
    async def login(self, username: str, password: str, security_code: str = None):
        """Login to PHPMaker through our authentication service."""
        print(f"🔐 Logging in user: {username}")
        
        try:
            login_data = {
                "username": username,
                "password": password
            }
            
            if security_code:
                login_data["security_code"] = security_code
            
            async with self.session.post(
                f"{self.api_base_url}/api/v1/phpmaker-auth/login",
                json=login_data
            ) as response:
                
                result = await response.json()
                
                if result.get('success'):
                    data = result['data']
                    self.session_id = data['session_id']
                    self.user_info = data
                    
                    print("✅ Login successful!")
                    print(f"   Session ID: {self.session_id}")
                    print(f"   Username: {data['username']}")
                    print(f"   User ID: {data['userid']}")
                    print(f"   User Level: {data['userlevel']}")
                    print(f"   Permission: {data['permission']}")
                    print(f"   Expires At: {data['expires_at']}")
                    
                    return True
                else:
                    print(f"❌ Login failed: {result.get('error', result.get('message'))}")
                    return False
                    
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    async def get_session_info(self):
        """Get current session information."""
        if not self.session_id:
            print("❌ No active session")
            return None
        
        print(f"📋 Getting session info for: {self.session_id}")
        
        try:
            async with self.session.get(
                f"{self.api_base_url}/api/v1/phpmaker-auth/session/{self.session_id}"
            ) as response:
                
                result = await response.json()
                
                if result.get('success'):
                    data = result['data']
                    print("✅ Session info retrieved:")
                    print(f"   Username: {data['username']}")
                    print(f"   User ID: {data['userid']}")
                    print(f"   User Level: {data['userlevel']}")
                    print(f"   Permission: {data['permission']}")
                    print(f"   Is Expired: {data['is_expired']}")
                    print(f"   Expires At: {data['expires_at']}")
                    return data
                else:
                    print(f"❌ Session info failed: {result}")
                    return None
                    
        except Exception as e:
            print(f"❌ Session info error: {e}")
            return None
    
    async def make_phpmaker_request(self, method: str, endpoint: str, data=None, json_data=None, params=None):
        """Make authenticated request to PHPMaker API."""
        if not self.session_id:
            print("❌ No active session for API request")
            return None
        
        print(f"🌐 Making PHPMaker API request: {method} {endpoint}")
        
        try:
            request_data = {
                "session_id": self.session_id,
                "method": method,
                "endpoint": endpoint
            }
            
            if data:
                request_data["data"] = data
            if json_data:
                request_data["json_data"] = json_data
            if params:
                request_data["params"] = params
            
            async with self.session.post(
                f"{self.api_base_url}/api/v1/phpmaker-auth/request",
                json=request_data
            ) as response:
                
                result = await response.json()
                
                if response.status == 200 and not result.get('error'):
                    print("✅ PHPMaker API request successful")
                    return result
                else:
                    print(f"❌ PHPMaker API request failed: {result}")
                    return result
                    
        except Exception as e:
            print(f"❌ PHPMaker API request error: {e}")
            return None
    
    async def logout(self):
        """Logout and invalidate session."""
        if not self.session_id:
            print("❌ No active session to logout")
            return
        
        print(f"🚪 Logging out session: {self.session_id}")
        
        try:
            async with self.session.delete(
                f"{self.api_base_url}/api/v1/phpmaker-auth/logout/{self.session_id}"
            ) as response:
                
                result = await response.json()
                
                if result.get('success'):
                    print("✅ Logout successful")
                    self.session_id = None
                    self.user_info = None
                else:
                    print(f"⚠️ Logout response: {result.get('message')}")
                    
        except Exception as e:
            print(f"❌ Logout error: {e}")


async def main():
    """Main test function."""
    print("🧪 PHPMaker Integration Test")
    print("=" * 60)
    
    # Check configuration
    print(f"📋 Configuration:")
    print(f"   API URL: {settings.phpmaker_api_url}")
    print(f"   Use SSL: {settings.phpmaker_use_ssl}")
    print()
    
    if not settings.phpmaker_api_url:
        print("❌ PHPMaker API URL not configured!")
        print("Please set PHPMAKER_API_URL environment variable")
        return
    
    async with PHPMakerIntegrationTest() as test:
        
        # Test 1: Connection test
        print("=" * 60)
        if not await test.test_connection():
            print("❌ Connection test failed, stopping tests")
            return
        
        print()
        
        # Test 2: Login (replace with actual credentials)
        print("=" * 60)
        print("🔐 Login Test")
        print("⚠️  Update the credentials below with actual PHPMaker credentials")
        
        # TODO: Replace these with actual credentials or prompt for input
        username = input("Enter PHPMaker username: ").strip()
        password = input("Enter PHPMaker password: ").strip()
        
        if not username or not password:
            print("❌ Username and password are required")
            return
        
        if not await test.login(username, password):
            print("❌ Login failed, stopping tests")
            return
        
        print()
        
        # Test 3: Session info
        print("=" * 60)
        print("📋 Session Info Test")
        await test.get_session_info()
        print()
        
        # Test 4: PHPMaker API requests (examples)
        print("=" * 60)
        print("🌐 PHPMaker API Request Tests")
        
        # Example 1: List records (replace 'cars' with actual table name)
        table_name = input("Enter table name to test (e.g., 'cars', or press Enter to skip): ").strip()
        
        if table_name:
            result = await test.make_phpmaker_request(
                method="GET",
                endpoint=f"list/{table_name}",
                params={"recperpage": 5}
            )
            
            if result and isinstance(result, dict):
                total_records = result.get('totalRecords', 'Unknown')
                records = result.get('records', [])
                print(f"   Total Records: {total_records}")
                print(f"   Records Returned: {len(records) if isinstance(records, list) else 'Unknown'}")
                
                # Show first record keys (without data for privacy)
                if records and isinstance(records, list) and len(records) > 0:
                    first_record = records[0]
                    if isinstance(first_record, dict):
                        print(f"   Record Fields: {list(first_record.keys())}")
        else:
            print("   Skipping table test")
        
        print()
        
        # Test 5: Session management
        print("=" * 60)
        print("🔄 Session Management Test")
        await test.get_session_info()
        print()
        
        # Test 6: Logout
        print("=" * 60)
        print("🚪 Logout Test")
        await test.logout()
        
        print()
        print("✅ All tests completed!")


if __name__ == "__main__":
    print("""
🚀 PHPMaker Integration Setup

Before running this test, make sure:

1. Set environment variable:
   PHPMAKER_API_URL=https://your-phpmaker-app.com/api

2. Your PHPMaker application has API enabled

3. You have valid PHPMaker user credentials

4. Your document processing API server is running on localhost:8000

""")
    
    asyncio.run(main()) 