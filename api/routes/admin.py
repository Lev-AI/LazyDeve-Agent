"""
Admin Routes - Administrative operations (requires authentication)
Extracted from agent.py for Task 7 Phase 2
"""

import os
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from core.lazydeve_boot import initializer

router = APIRouter()


@router.post("/admin/reset-init")
def reset_initialization(secret_key: str = Query(...)):
    """
    Reset initialization state (admin only).
    Requires secret key from environment variable ADMIN_SECRET_KEY.
    
    Args:
        secret_key: Admin secret key for authentication
    
    Returns:
        Initialization reset result or 401 Unauthorized
    """
    admin_key = os.getenv("ADMIN_SECRET_KEY", "change-me-in-production")
    
    if secret_key != admin_key:
        return JSONResponse(
            content={"status": "error", "message": "Unauthorized"},
            status_code=401
        )
    
    result = initializer.reset()
    return JSONResponse(content=result)

