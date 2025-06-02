#!/usr/bin/env python3
"""
PHPMaker Authentication API Endpoints

Provides endpoints for authenticating with PHPMaker and managing JWT tokens.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import redis
import json

from app.services.phpmaker_auth_service import get_phpmaker_auth
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Redis client for session storage
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True
)


class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., description="PHPMaker username")
    password: str = Field(..., description="PHPMaker password")
    security_code: Optional[str] = Field(None, description="2FA security code (if enabled)")


class LoginResponse(BaseModel):
    """Login response model."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AuthenticatedRequest(BaseModel):
    """Model for making authenticated requests to PHPMaker."""
    session_id: str = Field(..., description="Session ID from login")
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    endpoint: str = Field(..., description="PHPMaker API endpoint")
    data: Optional[Dict] = Field(None, description="Form data")
    json_data: Optional[Dict] = Field(None, description="JSON data")
    params: Optional[Dict] = Field(None, description="URL parameters")


@router.post("/login", response_model=LoginResponse)
async def login_to_phpmaker(
    request: LoginRequest,
    phpmaker_auth = Depends(get_phpmaker_auth)
):
    """
    Login to PHPMaker and get JWT token with user info.
    
    This endpoint:
    1. Authenticates user with PHPMaker API
    2. Returns JWT token and user information
    3. Stores session info in Redis for subsequent requests
    """
    try:
        logger.info(f"PHPMaker login attempt for user: {request.username}")
        
        # Login to PHPMaker
        login_result = await phpmaker_auth.login_user(
            username=request.username,
            password=request.password,
            security_code=request.security_code
        )
        
        if login_result.get('success'):
            # Generate session ID for this user
            import uuid
            session_id = str(uuid.uuid4())
            
            # Store session info in Redis (expires in 24 hours)
            session_data = {
                'jwt_token': login_result['jwt'],
                'username': login_result['username'],
                'userid': login_result['userid'],
                'userlevel': login_result['userlevel'],
                'permission': login_result['permission'],
                'expires_at': login_result['expires_at'],
                'values': login_result['values']
            }
            
            redis_client.setex(
                f"phpmaker_session:{session_id}",
                86400,  # 24 hours
                json.dumps(session_data)
            )
            
            logger.info(f"✅ PHPMaker login successful for user: {request.username}")
            
            return LoginResponse(
                success=True,
                message="Login successful",
                data={
                    'session_id': session_id,
                    'username': login_result['username'],
                    'userid': login_result['userid'],
                    'userlevel': login_result['userlevel'],
                    'permission': login_result['permission'],
                    'expires_at': login_result['expires_at'],
                    'user_info': login_result['values']
                }
            )
        else:
            logger.warning(f"❌ PHPMaker login failed for user: {request.username}")
            return LoginResponse(
                success=False,
                message="Login failed",
                error=login_result.get('error', 'Unknown error')
            )
            
    except Exception as e:
        logger.error(f"❌ PHPMaker login error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Login error: {str(e)}"
        )


@router.post("/request", response_model=Dict[str, Any])
async def make_phpmaker_request(
    request: AuthenticatedRequest,
    phpmaker_auth = Depends(get_phpmaker_auth)
):
    """
    Make authenticated request to PHPMaker API using session.
    
    This endpoint:
    1. Validates session and gets JWT token
    2. Makes authenticated request to PHPMaker API
    3. Returns the API response
    """
    try:
        # Get session data from Redis
        session_key = f"phpmaker_session:{request.session_id}"
        session_data_str = redis_client.get(session_key)
        
        if not session_data_str:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session"
            )
        
        session_data = json.loads(session_data_str)
        jwt_token = session_data['jwt_token']
        expires_at = session_data['expires_at']
        
        # Check if token is expired
        if phpmaker_auth.is_token_expired(expires_at):
            # Remove expired session
            redis_client.delete(session_key)
            raise HTTPException(
                status_code=401,
                detail="Session expired, please login again"
            )
        
        # Make authenticated request
        response = await phpmaker_auth.make_authenticated_request(
            jwt_token=jwt_token,
            method=request.method,
            endpoint=request.endpoint,
            data=request.data,
            json_data=request.json_data,
            params=request.params
        )
        
        logger.info(f"PHPMaker API request: {request.method} {request.endpoint}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PHPMaker API request error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"API request error: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get session information for a given session ID.
    
    Returns user info and session status.
    """
    try:
        session_key = f"phpmaker_session:{session_id}"
        session_data_str = redis_client.get(session_key)
        
        if not session_data_str:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        session_data = json.loads(session_data_str)
        
        # Remove sensitive info
        safe_session_data = {
            'username': session_data['username'],
            'userid': session_data['userid'],
            'userlevel': session_data['userlevel'],
            'permission': session_data['permission'],
            'expires_at': session_data['expires_at'],
            'is_expired': phpmaker_auth.is_token_expired(session_data['expires_at']),
            'user_info': session_data['values']
        }
        
        return {
            'success': True,
            'data': safe_session_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get session info error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Session info error: {str(e)}"
        )


@router.delete("/logout/{session_id}")
async def logout_session(session_id: str):
    """
    Logout and invalidate session.
    """
    try:
        session_key = f"phpmaker_session:{session_id}"
        deleted = redis_client.delete(session_key)
        
        if deleted:
            logger.info(f"✅ Session logged out: {session_id}")
            return {
                'success': True,
                'message': 'Logged out successfully'
            }
        else:
            return {
                'success': False,
                'message': 'Session not found or already expired'
            }
            
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Logout error: {str(e)}"
        )


@router.get("/test-connection")
async def test_phpmaker_connection(phpmaker_auth = Depends(get_phpmaker_auth)):
    """
    Test connection to PHPMaker API.
    """
    try:
        is_connected = await phpmaker_auth.test_connection()
        
        return {
            'success': is_connected,
            'message': 'Connection successful' if is_connected else 'Connection failed',
            'api_url': settings.phpmaker_api_url
        }
        
    except Exception as e:
        logger.error(f"❌ Connection test error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Connection test error: {str(e)}"
        ) 