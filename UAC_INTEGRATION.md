# UAC Authentication Integration

This document outlines the complete UAC (User Access Control) authentication integration that provides secure JWT-based authentication and session management.

## Overview

The UAC integration allows users to authenticate with their UAC system and make authenticated API requests through a secure session-based system. No credentials are hardcoded - all authentication is done dynamically with user-provided credentials.

## Files Modified/Created

### Core Configuration
- **`app/core/config.py`**: Updated UAC configuration settings
  - `UAC_API_URL`, `UAC_JWT_EXPIRE_HOURS`, `UAC_JWT_PERMISSION`, `UAC_USE_SSL`

### Service Layer
- **`app/services/uac_auth_service.py`** (renamed from `phpmaker_auth_service.py`)
  - `UACAuthService` class for JWT authentication
  - User login with dynamic credentials
  - Session management with Redis
  - Token validation and expiration handling

### API Layer  
- **`app/api/v1/uac_auth.py`** (renamed from `phpmaker_auth.py`)
  - REST API endpoints for UAC authentication
  - Session-based authentication flow
  - Redis session storage

### Main Application
- **`app/main.py`**: Updated router imports and endpoint registration
  - Routes now available at `/api/v1/uac-auth/*`

### Testing & Configuration
- **`test_uac_integration.py`** (renamed from `test_phpmaker_integration.py`)
- **`test_uac_auth.py`** (renamed from `test_phpmaker_auth.py`) 
- **`uac.env.template`** (renamed from `phpmaker.env.template`)

## Environment Configuration

Add these settings to your `.env` file:

```bash
# UAC API Configuration
UAC_API_URL=https://your-uac-app.com/api
UAC_JWT_EXPIRE_HOURS=24
UAC_USE_SSL=true
UAC_JWT_PERMISSION=1032  # Optional: specific permissions
```

## API Endpoints

### Authentication Flow

1. **Login**: `POST /api/v1/uac-auth/login`
   ```json
   {
     "username": "your_username",
     "password": "your_password"
   }
   ```
   Returns: Session ID and user information

2. **Make Requests**: `POST /api/v1/uac-auth/request`
   ```json
   {
     "session_id": "uuid",
     "method": "GET",
     "endpoint": "list/your_table",
     "params": {"recperpage": 10}
   }
   ```

3. **Session Info**: `GET /api/v1/uac-auth/session/{session_id}`

4. **Logout**: `DELETE /api/v1/uac-auth/logout/{session_id}`

5. **Test Connection**: `GET /api/v1/uac-auth/test-connection`

## Key Features

### Dynamic User Authentication
- No hardcoded credentials in configuration
- Users provide their own UAC username/password
- Secure session management with Redis storage

### JWT Token Management
- Automatic JWT extraction from UAC responses
- Support for multiple JWT response formats
- Token expiration handling with buffer time

### User Information Extraction
- Extracts user details (`userid`, `userlevel`, `permission`, etc.)
- Multiple extraction methods for different response formats
- JWT payload decoding as fallback

### Session Management
- UUID-based session IDs
- Redis storage with configurable expiration
- Session validation for all authenticated requests

## Usage Examples

### Direct Service Usage
```python
from app.services.uac_auth_service import uac_auth

# Login user
login_result = await uac_auth.login_user(username, password)

if login_result.get('success'):
    jwt_token = login_result['jwt']
    userid = login_result['userid']
    
    # Make authenticated request
    data = await uac_auth.make_authenticated_request(
        jwt_token=jwt_token,
        method='GET',
        endpoint='list/cars',
        params={'recperpage': 10}
    )
```

### REST API Usage
```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/uac-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 2. Make authenticated request  
curl -X POST http://localhost:8000/api/v1/uac-auth/request \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "method": "GET", 
    "endpoint": "list/cars",
    "params": {"recperpage": 5}
  }'
```

## Testing

Run the integration tests:

```bash
# Test service directly
python test_uac_auth.py

# Test full integration
python test_uac_integration.py
```

## Security Features

- JWT-based authentication
- Session expiration management
- SSL/TLS support configuration
- Secure credential handling (no storage)
- Session invalidation on logout

## File Manager Integration

The UAC authentication provides the `userid` and `userlevel` fields required by the file manager for user access control and personalization.

## Migration from PHPMaker

All references to "PHPMaker" have been updated to "UAC":
- Environment variables: `PHPMAKER_*` → `UAC_*`
- API endpoints: `/phpmaker-auth/*` → `/uac-auth/*`
- Service names: `PHPMakerAuthService` → `UACAuthService`
- Function names and variables updated accordingly

The functionality remains the same - only the naming has been changed for clarity and generalization. 