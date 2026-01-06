"""
Protection Routes - System protection and file operation validation
Extracted from agent.py for Task 7 Phase 2
"""

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from core.system_protection import (
    get_protection_status,
    list_protected_files,
    check_file_operation_protection
)

router = APIRouter()


@router.get("/protection-status")
def get_protection_status_endpoint():
    """
    Get current system protection status and configuration.
    Returns protected files list and protection rules.
    """
    try:
        status = get_protection_status()
        protected_files = list_protected_files()
        
        return JSONResponse({
            "status": "success",
            "protection_status": status,
            "protected_files": protected_files,
            "message": "System protection is active"
        })
        
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": "Failed to get protection status", "error": str(e)},
            status_code=500
        )


@router.post("/check-protection")
def check_file_protection(path: str = Body(...), operation: str = Body("update")):
    """
    Check if a file operation is allowed under current protection rules.
    
    Args:
        path: File path to check
        operation: Operation type (update, delete, create)
    
    Returns:
        Protection check result with allowed/blocked status
    """
    try:
        result = check_file_operation_protection(path, operation)
        
        return JSONResponse({
            "status": "success",
            "protection_check": result,
            "path": path,
            "operation": operation
        })
        
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": "Failed to check protection", "error": str(e)},
            status_code=500
        )

