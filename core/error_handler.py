"""
error_handler.py
----------------
Unified Error Handler for LazyDeve Agent.
Task 7.7.9 — Introduce Unified Error Handler

Provides centralized error reporting with consistent structure.
All modules produce consistent error structures → easier for Semantic Memory to detect error patterns.
"""

import traceback
from typing import Dict, Any, Optional
from core.log_manager import LogManager

# Initialize logger
logger = LogManager()

def handle_error(project: str, source: str, exc: Exception, extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Centralized error reporting with consistent structure.
    
    Args:
        project: Project name where error occurred
        source: Source function/module where error occurred
        exc: Exception object
        extra_data: Optional additional data to include
        
    Returns:
        dict: Consistent error structure with status, message, and details
    """
    try:
        # Create error message
        error_type = type(exc).__name__
        error_message = str(exc)
        msg = f"{source}: {error_type} - {error_message}"
        
        # Log the error
        logger.log(project, "ERROR", msg)
        
        # Create structured error response
        error_response = {
            "status": "error",
            "message": msg,
            "error_type": error_type,
            "error_message": error_message,
            "source": source,
            "project": project
        }
        
        # Add extra data if provided
        if extra_data:
            error_response["extra_data"] = extra_data
        
        # Add traceback for debugging (optional)
        error_response["traceback"] = traceback.format_exc()
        
        return error_response
        
    except Exception as log_error:
        # Fallback if logging fails
        return {
            "status": "error",
            "message": f"Error in error handler: {str(log_error)}",
            "original_error": f"{source}: {type(exc).__name__} - {str(exc)}",
            "source": source,
            "project": project
        }

def handle_warning(project: str, source: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Centralized warning reporting with consistent structure.
    
    Args:
        project: Project name where warning occurred
        source: Source function/module where warning occurred
        message: Warning message
        extra_data: Optional additional data to include
        
    Returns:
        dict: Consistent warning structure
    """
    try:
        # Log the warning
        logger.log(project, "WARNING", f"{source}: {message}")
        
        # Create structured warning response
        warning_response = {
            "status": "warning",
            "message": f"{source}: {message}",
            "source": source,
            "project": project
        }
        
        # Add extra data if provided
        if extra_data:
            warning_response["extra_data"] = extra_data
        
        return warning_response
        
    except Exception as log_error:
        # Fallback if logging fails
        return {
            "status": "warning",
            "message": f"Warning in warning handler: {str(log_error)}",
            "original_warning": f"{source}: {message}",
            "source": source,
            "project": project
        }

def handle_success(project: str, source: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Centralized success reporting with consistent structure.
    
    Args:
        project: Project name where success occurred
        source: Source function/module where success occurred
        message: Success message
        extra_data: Optional additional data to include
        
    Returns:
        dict: Consistent success structure
    """
    try:
        # Log the success
        logger.log(project, "INFO", f"{source}: {message}")
        
        # Create structured success response
        success_response = {
            "status": "success",
            "message": f"{source}: {message}",
            "source": source,
            "project": project
        }
        
        # Add extra data if provided
        if extra_data:
            success_response["extra_data"] = extra_data
        
        return success_response
        
    except Exception as log_error:
        # Fallback if logging fails
        return {
            "status": "success",
            "message": f"Success in success handler: {str(log_error)}",
            "original_success": f"{source}: {message}",
            "source": source,
            "project": project
        }

def is_error_response(response: Dict[str, Any]) -> bool:
    """
    Check if a response indicates an error.
    
    Args:
        response: Response dictionary to check
        
    Returns:
        bool: True if response indicates an error
    """
    return response.get("status") == "error"

def is_success_response(response: Dict[str, Any]) -> bool:
    """
    Check if a response indicates success.
    
    Args:
        response: Response dictionary to check
        
    Returns:
        bool: True if response indicates success
    """
    return response.get("status") == "success"

def extract_error_message(response: Dict[str, Any]) -> str:
    """
    Extract error message from error response.
    
    Args:
        response: Error response dictionary
        
    Returns:
        str: Error message or empty string if not an error
    """
    if is_error_response(response):
        return response.get("message", "")
    return ""

def extract_success_message(response: Dict[str, Any]) -> str:
    """
    Extract success message from success response.
    
    Args:
        response: Success response dictionary
        
    Returns:
        str: Success message or empty string if not a success
    """
    if is_success_response(response):
        return response.get("message", "")
    return ""

