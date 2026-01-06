"""
context_api.py
--------------
Task 7.7.10 — Context Access API Layer for LazyDeve Agent.
Provides simple access to project context summaries from .lazydeve/memory.json.

This is preparation for Task 8 (Semantic Context Memory).
Currently returns empty dict until context_summary field is populated.
"""

from core.memory_utils import load_memory
from typing import Dict, Any
import requests

def get_project_context(project_name: str) -> Dict[str, Any]:
    """
    Task 7.7.10 — Get project context summary from memory.
    
    Loads project memory and extracts the context_summary field.
    This provides quick access to project context without scanning files.
    
    Args:
        project_name: Name of the project
        
    Returns:
        dict: Context summary (empty dict if not available or project not found)
    """
    memory = load_memory(project_name)
    return memory.get("context_summary", {}) if memory else {}

def get_context_snapshot(project_name: str) -> Dict[str, Any]:
    """
    Get the context snapshot for a project via a GET request.
    
    Args:
        project_name: Name of the project
        
    Returns:
        dict: Context snapshot response
    """
    url = f"/context/snapshot?project={project_name}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {}
