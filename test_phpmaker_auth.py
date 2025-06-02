#!/usr/bin/env python3
"""
Test PHPMaker Authentication Service

This script demonstrates how to use the PHPMaker authentication service
with dynamic user credentials (no hardcoded username/password).

Usage:
1. Set PHPMAKER_API_URL environment variable
2. Run this script and provide credentials when prompted
"""

import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.phpmaker_auth_service import phpmaker_auth
from app.core.config import settings


async def test_phpmaker_auth():
    """Test PHPMaker authentication service with dynamic credentials."""
    
    print("🧪 Testing PHPMaker Authentication Service")
    print("=" * 60)
    
    # Check configuration
    print(f"📋 Configuration:")
    print(f"   API URL: {settings.phpmaker_api_url}")
    print(f"   Expire Hours: {settings.phpmaker_jwt_expire_hours}")
    print(f"   Permission: {settings.phpmaker_jwt_permission}")
    print(f"   Use SSL: {settings.phpmaker_use_ssl}")
    print()
    
    # Check if basic configuration is complete
    if not settings.phpmaker_api_url:
        print("❌ PHPMaker configuration incomplete!")
        print("Please set PHPMAKER_API_URL environment variable")
        print("Example: PHPMAKER_API_URL=https://your-app.com/api")
        return
    
    try:
        # Test 1: Connection test
        print("🔗 Test 1: Testing connection...")
        is_connected = await phpmaker_auth.test_connection()
        
        if is_connected:
            print("✅ Connection successful!")
        else:
            print("❌ Connection failed!")
            return
        
        print()
        
        # Test 2: Get user credentials
        print("🔐 Test 2: User Authentication")
        username = input("Enter PHPMaker username: ").strip()
        password = input("Enter PHPMaker password: ").strip()
        
        if not username or not password:
            print("❌ Username and password are required")
            return
        
        # Test 3: Login user
        print(f"🎫 Test 3: Logging in user: {username}")
        login_result = await phpmaker_auth.login_user(username, password)
        
        if login_result.get('success'):
            print("✅ Login successful!")
            print(f"   Username: {login_result['username']}")
            print(f"   User ID: {login_result['userid']}")
            print(f"   User Level: {login_result['userlevel']}")
            print(f"   Permission: {login_result['permission']}")
            print(f"   Expires At: {login_result['expires_at']}")
            
            jwt_token = login_result['jwt']
            print(f"   JWT Token (first 50 chars): {jwt_token[:50]}...")
            
        else:
            print(f"❌ Login failed: {login_result.get('error')}")
            return
        
        print()
        
        # Test 4: Make authenticated request (example)
        print("🌐 Test 4: Making authenticated request...")
        
        # Ask for table name to test
        table_name = input("Enter table name to test (e.g., 'cars', or press Enter to skip): ").strip()
        
        if table_name:
            try:
                response = await phpmaker_auth.make_authenticated_request(
                    jwt_token=jwt_token,
                    method='GET',
                    endpoint=f'list/{table_name}',
                    params={'recperpage': 5}
                )
                
                if response.get('success') is False:
                    print(f"   ⚠️ API request failed: {response.get('error')}")
                else:
                    print(f"   ✅ API request successful!")
                    if isinstance(response, dict):
                        total_records = response.get('totalRecords', 'Unknown')
                        records = response.get('records', [])
                        print(f"   Total Records: {total_records}")
                        print(f"   Records Returned: {len(records) if isinstance(records, list) else 'Unknown'}")
            
            except Exception as e:
                print(f"   ⚠️ API request error: {e}")
        else:
            print("   Skipping API request test")
        
        print()
        
        # Test 5: Token expiration check
        print("🔄 Test 5: Token expiration check...")
        expires_at = login_result['expires_at']
        is_expired = phpmaker_auth.is_token_expired(expires_at)
        print(f"   Token expires at: {expires_at}")
        print(f"   Is expired: {is_expired}")
        print()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await phpmaker_auth.close()
        print("🧹 Cleaned up resources")


async def example_integration():
    """Example of how to integrate PHPMaker auth in your application."""
    
    print("\n" + "=" * 60)
    print("📋 Integration Example - New Dynamic API")
    print("=" * 60)
    
    print("""
    # Updated integration using dynamic credentials:
    
    from app.services.phpmaker_auth_service import phpmaker_auth
    
    # 1. Login user with their credentials
    login_result = await phpmaker_auth.login_user(username, password)
    
    if login_result.get('success'):
        jwt_token = login_result['jwt']
        userid = login_result['userid']
        userlevel = login_result['userlevel']
        
        # 2. Make authenticated requests using the JWT token
        data = await phpmaker_auth.make_authenticated_request(
            jwt_token=jwt_token,
            method='GET', 
            endpoint='list/your_table',
            params={'recperpage': 10}
        )
        
        # 3. Add new record
        new_record = await phpmaker_auth.make_authenticated_request(
            jwt_token=jwt_token,
            method='POST',
            endpoint='add/your_table',
            data={'field1': 'value1', 'field2': 'value2'}
        )
        
        # 4. Update record  
        updated = await phpmaker_auth.make_authenticated_request(
            jwt_token=jwt_token,
            method='POST',
            endpoint='edit/your_table/123',
            data={'field1': 'new_value'}
        )
        
        # 5. Delete record
        deleted = await phpmaker_auth.make_authenticated_request(
            jwt_token=jwt_token,
            method='GET',
            endpoint='delete/your_table/123'
        )
    
    # =====================================================================
    # OR use the REST API endpoints:
    # =====================================================================
    
    # 1. Login via API
    POST /api/v1/phpmaker-auth/login
    {
        "username": "your_username",
        "password": "your_password"
    }
    # Returns: {"session_id": "uuid", "userid": "-1", ...}
    
    # 2. Make authenticated requests via API
    POST /api/v1/phpmaker-auth/request
    {
        "session_id": "session_uuid",
        "method": "GET",
        "endpoint": "list/your_table",
        "params": {"recperpage": 10}
    }
    # Returns: PHPMaker API response
    
    # 3. Get session info
    GET /api/v1/phpmaker-auth/session/{session_id}
    
    # 4. Logout
    DELETE /api/v1/phpmaker-auth/logout/{session_id}
    """)


if __name__ == "__main__":
    print("""
🚀 PHPMaker Authentication Test - Dynamic Credentials

This test now uses dynamic user credentials instead of hardcoded config.
You'll be prompted to enter your PHPMaker username and password.

Setup required:
1. Set PHPMAKER_API_URL environment variable
2. Ensure your PHPMaker application has API enabled
3. Have valid PHPMaker user credentials ready

""")
    
    # Run tests
    asyncio.run(test_phpmaker_auth())
    asyncio.run(example_integration()) 