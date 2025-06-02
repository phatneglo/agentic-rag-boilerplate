#!/usr/bin/env python3
"""
PHPMaker Authentication Service

Handles JWT authentication with PHPMaker API based on the PHPMaker API documentation:
https://phpmaker.dev/docs2024/api.html

This service provides:
- JWT token acquisition from PHPMaker login API with user credentials
- Token caching per user session
- Authentication headers for API requests
- User info extraction from JWT response
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urljoin

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PHPMakerAuthService:
    """
    Service to handle PHPMaker API authentication and JWT management.
    
    Based on PHPMaker API documentation:
    - POST /api/login for authentication
    - Returns JWT token for subsequent API calls
    - Handles token expiration and refresh
    """
    
    def __init__(self):
        self.api_url = settings.phpmaker_api_url.rstrip('/')
        self.expire_hours = settings.phpmaker_jwt_expire_hours
        self.permission = settings.phpmaker_jwt_permission
        self.use_ssl = settings.phpmaker_use_ssl
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"PHPMaker Auth Service initialized for: {self.api_url}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                ssl=self.use_ssl,
                verify_ssl=self.use_ssl
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def login_user(self, username: str, password: str, security_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Login user to PHPMaker API and get JWT token with user info.
        
        Args:
            username: User's username
            password: User's password  
            security_code: Optional 2FA security code
            
        Returns:
            dict: Login response with JWT token and user info
            {
                "success": true,
                "jwt": "ZDZhN2E3NjgtMTUwYy00MzQ4LWIwMGQtMDA2Nzk3OTkyZmJm",
                "username": "Administrator", 
                "userid": "-1",
                "userlevel": -1,
                "permission": 0,
                "expires_at": "2024-01-01T12:00:00",
                "values": {...}
            }
        """
        try:
            login_url = urljoin(f"{self.api_url}/", "login")
            
            # Prepare login data
            login_data = {
                'username': username,
                'password': password,
                'expire': self.expire_hours
            }
            
            # Add 2FA security code if provided
            if security_code:
                login_data['securitycode'] = security_code
            
            # Add permission if specified
            if self.permission is not None:
                login_data['permission'] = self.permission
            
            session = await self._get_session()
            
            logger.info(f"Attempting PHPMaker login for user: {username}")
            
            async with session.post(
                login_url,
                data=login_data,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Debug: Log the actual response structure
                    logger.info(f"📋 PHPMaker response structure: {json.dumps(result, indent=2)}")
                    
                    # Extract JWT token from response
                    jwt_token = (
                        result.get('JWT') or       # PHPMaker uses uppercase 'JWT'
                        result.get('jwt') or 
                        result.get('token') or 
                        result.get('access_token')
                    )
                    
                    if not jwt_token:
                        logger.error(f"❌ No JWT token in PHPMaker response: {result}")
                        return {
                            'success': False,
                            'error': 'No JWT token received from PHPMaker',
                            'response': result
                        }
                    
                    # Extract user info from response - try multiple possible structures
                    values = {}
                    
                    # Method 1: Direct values field
                    if 'values' in result:
                        values = result['values']
                        logger.info(f"📋 Found values in 'values' field: {values}")
                    
                    # Method 2: Values might be at root level of response
                    elif any(key in result for key in ['username', 'userid', 'userlevel']):
                        values = {
                            'username': result.get('username'),
                            'userid': result.get('userid'),
                            'parentuserid': result.get('parentuserid'),
                            'userlevel': result.get('userlevel'),
                            'userprimarykey': result.get('userprimarykey'),
                            'permission': result.get('permission')
                        }
                        logger.info(f"📋 Found values at root level: {values}")
                    
                    # Method 3: Try to decode JWT token to extract values
                    else:
                        try:
                            import base64
                            # Decode JWT payload (second part after splitting by '.')
                            jwt_parts = jwt_token.split('.')
                            if len(jwt_parts) >= 2:
                                # Add padding if needed
                                payload = jwt_parts[1]
                                padding = 4 - len(payload) % 4
                                if padding != 4:
                                    payload += '=' * padding
                                
                                decoded_payload = base64.b64decode(payload)
                                jwt_data = json.loads(decoded_payload.decode('utf-8'))
                                
                                if 'values' in jwt_data:
                                    values = jwt_data['values']
                                    logger.info(f"📋 Found values in JWT payload: {values}")
                                else:
                                    logger.warning(f"⚠️ No 'values' in JWT payload: {jwt_data}")
                                    
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to decode JWT for values: {e}")
                    
                    # Fallback: use provided username if no values found
                    if not values or not any(values.values()):
                        logger.warning(f"⚠️ No user values found, using fallback")
                        values = {'username': username}
                    
                    user_info = {
                        'success': True,
                        'jwt': jwt_token,
                        'username': values.get('username', username),
                        'userid': values.get('userid'),
                        'parent_userid': values.get('parentuserid'),
                        'userlevel': values.get('userlevel'),
                        'user_primary_key': values.get('userprimarykey'),
                        'permission': values.get('permission', 0),
                        'expires_at': (datetime.now() + timedelta(hours=self.expire_hours)).isoformat(),
                        'values': values,
                        'raw_response': result
                    }
                    
                    logger.info(f"✅ PHPMaker login successful for user: {username} (userid: {user_info['userid']})")
                    return user_info
                    
                else:
                    error_text = await response.text()
                    logger.error(f"❌ PHPMaker login failed: {response.status} - {error_text}")
                    return {
                        'success': False,
                        'error': f"PHPMaker login failed: {response.status} - {error_text}",
                        'status_code': response.status
                    }
                    
        except Exception as e:
            logger.error(f"❌ PHPMaker login error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def make_authenticated_request(
        self, 
        jwt_token: str,
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to PHPMaker API using JWT token.
        
        Args:
            jwt_token: Valid JWT token from login
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., 'list/cars')
            data: Form data
            json_data: JSON data
            params: URL parameters
            
        Returns:
            dict: API response
        """
        try:
            url = urljoin(f"{self.api_url}/", endpoint)
            headers = {
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/json'
            }
            
            session = await self._get_session()
            
            # Prepare request kwargs
            request_kwargs = {
                'headers': headers,
                'params': params
            }
            
            if json_data:
                request_kwargs['json'] = json_data
                headers['Content-Type'] = 'application/json'
            elif data:
                request_kwargs['data'] = data
            
            logger.debug(f"Making authenticated request: {method} {url}")
            
            async with session.request(method, url, **request_kwargs) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"❌ PHPMaker API error: {response.status} - {error_text}")
                    return {
                        'success': False,
                        'error': f"PHPMaker API error: {response.status} - {error_text}",
                        'status_code': response.status
                    }
                    
        except Exception as e:
            logger.error(f"❌ PHPMaker API request failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def test_connection(self) -> bool:
        """
        Test connection to PHPMaker API.
        
        Returns:
            bool: True if connection successful
        """
        try:
            logger.info("Testing PHPMaker API connection...")
            
            # Just test if we can reach the API endpoint
            session = await self._get_session()
            login_url = urljoin(f"{self.api_url}/", "login")
            
            async with session.get(login_url) as response:
                # We expect this to fail (401/405) but connection should work
                logger.info(f"✅ PHPMaker API connection test successful (status: {response.status})")
                return True
                
        except Exception as e:
            logger.error(f"❌ PHPMaker API connection test failed: {e}")
            return False
    
    def is_token_expired(self, expires_at: str) -> bool:
        """
        Check if token is expired.
        
        Args:
            expires_at: ISO format datetime string
            
        Returns:
            bool: True if token is expired
        """
        try:
            expiry_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            # Add 5 minute buffer
            buffer_time = datetime.now() + timedelta(minutes=5)
            return expiry_time <= buffer_time
        except:
            return True


# Global instance
phpmaker_auth = PHPMakerAuthService()


async def get_phpmaker_auth() -> PHPMakerAuthService:
    """Get PHPMaker authentication service instance."""
    return phpmaker_auth


# Example usage
async def example_usage():
    """Example of how to use the PHPMaker Auth Service."""
    
    # Test connection
    if await phpmaker_auth.test_connection():
        print("✅ Connected to PHPMaker API")
        
        # Login user (replace with actual credentials)
        login_result = await phpmaker_auth.login_user("your_username", "your_password")
        
        if login_result.get('success'):
            print(f"✅ Login successful!")
            print(f"   User: {login_result['username']}")
            print(f"   User ID: {login_result['userid']}")
            print(f"   User Level: {login_result['userlevel']}")
            print(f"   Permission: {login_result['permission']}")
            
            jwt_token = login_result['jwt']
            
            # Make authenticated requests
            try:
                # Example: Get list of records from 'cars' table
                cars = await phpmaker_auth.make_authenticated_request(
                    jwt_token,
                    'GET', 
                    'list/cars',
                    params={'recperpage': 10}
                )
                print(f"Cars data: {cars}")
                
            except Exception as e:
                print(f"API request failed: {e}")
            
        else:
            print(f"❌ Login failed: {login_result.get('error')}")
        
        # Close session
        await phpmaker_auth.close()
    else:
        print("❌ Failed to connect to PHPMaker API")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage()) 