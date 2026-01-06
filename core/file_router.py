"""
file_router.py
--------------
Task 7.7.11-A — Context-Aware File Generation Utility
Provides path routing for active project-based file operations.

⚠️ IMPORTANT: This is a UTILITY MODULE ONLY
This module is NOT yet integrated into agent.py endpoints.
Integration requires careful analysis and testing to avoid breaking:
- /execute endpoint (Aider CLI behavior)
- /update-file endpoint (existing file operations)
- /run-tests endpoint (test file creation)

# FUTURE GOAL:
# When a project is active via ContextManager, this module will automatically
# route file creation/update operations to: projects/{active_project}/{relative_path}
# 
# Example Usage (NOT YET IMPLEMENTED):
#   from core.file_router import get_project_path
#   
#   # If active_project = "MyApp"
#   path = get_project_path("src/main.py")
#   # Returns: "projects/MyApp/src/main.py"
#   
#   # If no active project
#   path = get_project_path("src/main.py")
#   # Returns: "src/main.py" (fallback to root)

# INTEGRATION REQUIREMENTS (Future Work):
# 1. Analyze current file creation patterns in agent.py
# 2. Test Aider CLI working directory behavior with project folders
# 3. Identify which endpoints need project-aware file routing
# 4. Implement gradual integration with comprehensive testing
# 5. Ensure backward compatibility (no breaking changes)
"""

import os
from typing import Optional
from core.context_manager import context_manager


def get_project_path(relative_path: str) -> str:
    """
    Task 7.7.11-A — Route file path to active project directory if one is set.
    
    This function checks if there's an active project in ContextManager.
    If yes, it prepends 'projects/{project_name}/' to the relative path.
    If no active project is set, it returns the path unchanged (root fallback).
    
    ⚠️ NOTE: This function is NOT yet integrated into agent.py endpoints.
    It serves as a preparation for future project-aware file operations.
    
    Args:
        relative_path: Relative file path (e.g., "src/main.py", "tests/test_foo.py")
        
    Returns:
        str: Full path - either "projects/{project}/path" or original "path"
        
    Example:
        >>> # With active project "MyApp"
        >>> get_project_path("src/main.py")
        'projects/MyApp/src/main.py'
        
        >>> # Without active project
        >>> get_project_path("src/main.py")
        'src/main.py'
    """
    active_project = context_manager.get_project()
    
    if active_project:
        # Active project exists - route to project directory
        project_path = os.path.join("projects", active_project, relative_path)
        return os.path.normpath(project_path)
    
    # No active project - fallback to root directory behavior
    return relative_path


def is_project_active() -> bool:
    """
    Check if there's an active project set in ContextManager.
    
    Returns:
        bool: True if a project is active, False otherwise
    """
    return context_manager.get_project() is not None


def get_active_project() -> Optional[str]:
    """
    Get the currently active project name.
    
    Returns:
        Optional[str]: Project name if active, None otherwise
    """
    return context_manager.get_project()


# ===============================
# Future Integration Points
# ===============================
# 
# The following endpoints will need project-aware routing in the future:
# 
# 1. /execute endpoint (agent.py)
#    - Challenge: Aider CLI operates in current working directory
#    - Solution: Change working directory OR pass full paths to Aider
#    
# 2. /update-file endpoint (agent.py)
#    - Challenge: Direct file writes need path transformation
#    - Solution: Wrap file operations with get_project_path()
#    
# 3. /run-tests endpoint (agent.py)
#    - Challenge: Test file creation location
#    - Solution: Route test files to projects/{project}/tests/
#    
# 4. basic_functional.py operations
#    - Challenge: Multiple file operations across codebase
#    - Solution: Gradual refactoring with fallback behavior
#
# INTEGRATION STRATEGY:
# Phase 1: Add optional project parameter to file operations
# Phase 2: Use get_project_path() when project is specified
# Phase 3: Make project-aware routing default behavior
# Phase 4: Remove fallback behavior (require project context)







