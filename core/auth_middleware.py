"""
auth_middleware.py
------------------
Optional Bearer token authentication middleware for LazyDeve Agent.

This module provides environment-controlled authentication that can be toggled
via .env variables, allowing flexible security configuration for development
and production environments.

Usage:
    from core.auth_middleware import verify_token
    from fastapi import Depends
    
    @app.post("/execute", dependencies=[Depends(verify_token)])
    async def execute_task(...):
        # Endpoint is protected when ENABLE_AUTH=true
        ...

Environment Variables:
    API_BEARER_TOKEN: The secret token for authentication (default: "dev-token")
    ENABLE_AUTH: Enable/disable authentication (default: "false")
                 Set to "true" in production
"""

from fastapi import Request, HTTPException
import os
from typing import Optional

# ===============================
# Configuration
# ===============================

# Load token from environment (default to dev-token for safety)
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN", "dev-token")

# Authentication toggle - defaults to FALSE for development safety
# Set ENABLE_AUTH=true in production .env
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").strip().lower() == "true"

# ===============================
# Authentication Middleware
# ===============================

async def verify_token(request: Request) -> None:
    """
    Optional authentication middleware for FastAPI endpoints.
    
    Behavior:
        - If ENABLE_AUTH=false → Skip authentication (development mode)
        - If ENABLE_AUTH=true → Require valid Bearer token
    
    Args:
        request: FastAPI Request object
        
    Raises:
        HTTPException: 401 Unauthorized if token is missing or invalid
        
    Example:
        # In agent.py:
        @app.post("/execute", dependencies=[Depends(verify_token)])
        async def execute_task(...):
            # This endpoint is now protected
            ...
    """
    # Skip authentication if disabled (development/testing mode)
    if not ENABLE_AUTH:
        return
    
    # Extract Authorization header
    auth_header: Optional[str] = request.headers.get("Authorization")
    
    # Check if header exists and matches expected format
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing Authorization header"
        )
    
    # Validate Bearer token
    expected_auth = f"Bearer {API_BEARER_TOKEN}"
    if auth_header != expected_auth:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid Bearer token"
        )
    
    # Authentication successful - continue to endpoint
    return


# ===============================
# Utility Functions
# ===============================

def get_auth_status() -> dict:
    """
    Get current authentication configuration status.
    
    Returns:
        dict: Authentication status information
        
    Example:
        >>> from core.auth_middleware import get_auth_status
        >>> status = get_auth_status()
        >>> print(status)
        {'enabled': False, 'token_configured': True, 'environment': 'development'}
    """
    return {
        "enabled": ENABLE_AUTH,
        "token_configured": API_BEARER_TOKEN != "dev-token",
        "environment": "production" if ENABLE_AUTH else "development",
        "token_length": len(API_BEARER_TOKEN) if API_BEARER_TOKEN else 0
    }


def is_auth_enabled() -> bool:
    """
    Check if authentication is currently enabled.
    
    Returns:
        bool: True if authentication is enabled, False otherwise
    """
    return ENABLE_AUTH


# ===============================
# Module Information
# ===============================

__all__ = [
    'verify_token',
    'get_auth_status',
    'is_auth_enabled',
    'API_BEARER_TOKEN',
    'ENABLE_AUTH'
]

if __name__ == "__main__":
    # Module self-test
    print("Authentication Middleware Module - Configuration")
    print("=" * 50)
    status = get_auth_status()
    print(f"Authentication enabled: {status['enabled']}")
    print(f"Token configured: {status['token_configured']}")
    print(f"Environment: {status['environment']}")
    print(f"Token length: {status['token_length']}")
    print("=" * 50)
    
    if not ENABLE_AUTH:
        print("⚠️  WARNING: Authentication is DISABLED")
        print("   Set ENABLE_AUTH=true in .env for production")
    else:
        print("✅ Authentication is ENABLED")
        if API_BEARER_TOKEN == "dev-token":
            print("⚠️  WARNING: Using default dev-token")
            print("   Set API_BEARER_TOKEN in .env")

