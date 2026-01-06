"""
API Dependencies - Shared validation and utilities
"""

import re
import os
from pathlib import Path
from fastapi import HTTPException, status


def validate_project_exists(project_name: str) -> str:
    """
    Validate that a project exists.
    
    Args:
        project_name: Name of the project
        
    Returns:
        Project name if valid
        
    Raises:
        HTTPException: If project doesn't exist
    """
    # Use filesystem check for better testability
    project_path = Path(f"projects/{project_name}")
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_name}' not found"
        )
    return project_name


def validate_project_name(project_name: str) -> str:
    """
    Validate project name format.
    
    Args:
        project_name: Name to validate
        
    Returns:
        Project name if valid
        
    Raises:
        HTTPException: If name is invalid
    """
    if not project_name or not (3 <= len(project_name) <= 50):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name must be 3-50 characters"
        )
    
    if not re.match(r"^[a-zA-Z0-9_-]+$", project_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name must contain only alphanumeric characters, hyphens, or underscores"
        )
    
    return project_name

