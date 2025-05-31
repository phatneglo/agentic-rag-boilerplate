"""
JWT Authentication utilities for File Manager

Provides JWT token creation, validation, and user authentication
for scoped file access in user-specific directories.
"""

import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# JWT Configuration - Update these in your .env file
JWT_SECRET_KEY = "your-super-secret-jwt-key-change-this-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security scheme for FastAPI
security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data model."""
    userid: str
    username: str
    email: Optional[str] = None
    exp: int
    iat: int


class JWTService:
    """JWT token service for authentication."""
    
    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        self.expiration_hours = JWT_EXPIRATION_HOURS
    
    def create_token(self, userid: str, username: str, email: str = None) -> str:
        """
        Create a JWT token for a user.
        
        Args:
            userid: Unique user identifier
            username: Username
            email: Optional email address
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        expire = now + timedelta(hours=self.expiration_hours)
        
        payload = {
            "userid": userid,
            "username": username,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp())
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.info(f"Created JWT token for user: {username} (userid: {userid})")
        return token
    
    def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData object with user information
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate required fields
            userid = payload.get("userid")
            username = payload.get("username")
            
            if not userid or not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user information"
                )
            
            token_data = TokenData(
                userid=userid,
                username=username,
                email=payload.get("email"),
                exp=payload.get("exp"),
                iat=payload.get("iat")
            )
            
            logger.debug(f"Token verified for user: {username} (userid: {userid})")
            return token_data
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token verification failed: expired signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def create_sample_token(self) -> str:
        """
        Create a sample JWT token for testing.
        
        Returns:
            Sample JWT token string
        """
        return self.create_token(
            userid="user123",
            username="sampleuser",
            email="sample@example.com"
        )


# Create service instance
jwt_service = JWTService()


# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    FastAPI dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        TokenData object with user information
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required"
        )
    
    token = credentials.credentials
    return jwt_service.verify_token(token)


def get_user_directory(user: TokenData) -> str:
    """
    Get the user's scoped directory path.
    
    Args:
        user: TokenData object with user information
        
    Returns:
        User's directory path
    """
    return f"user-files/{user.userid}"


# Sample token for testing (you can use this in your frontend)
SAMPLE_JWT_TOKEN = jwt_service.create_sample_token()

# Log the sample token for easy copy-paste
logger.info(f"Sample JWT Token: {SAMPLE_JWT_TOKEN}") 