"""
File Routes - File read/write operations
Extracted from agent.py for Task 7 Phase 2
"""

import os
from fastapi import APIRouter, Request, Body, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
from core.auth_middleware import verify_token
from core.basic_functional import update_file, log_message

router = APIRouter()


@router.post("/read-file")
async def read_file_endpoint(request: Request):
    """
    Read file contents from the given path (supports both JSON and plain text body).
    ✅ BUG-FIX 2: Auto-inject project path like /update-file does
    
    Args:
        path: File path to read (from JSON body or plain text)
    
    Returns:
        File contents with status
    """
    try:
        # Try JSON body first
        try:
            data = await request.json()
            path = data.get("path")
        except Exception:
            path = (await request.body()).decode().strip()

        if not path:
            return JSONResponse({"status": "error", "message": "File path missing"}, status_code=400)

        # ✅ BUG-FIX 2: Auto-inject project path (same logic as /update-file)
        from core.context_manager import context_manager
        active_project = context_manager.get_project()
        
        if active_project:
            # Normalize path separators
            normalized_path = path.replace("\\", "/")
            
            # Auto-prefix if not already prefixed with projects/
            if not normalized_path.startswith("projects/"):
                path = os.path.join("projects", active_project, path)
                log_message(f"[Reader] Auto-prefixed path to active project: {path}")
            elif not normalized_path.startswith(f"projects/{active_project}/"):
                # Path is in different project - return error
                return JSONResponse({
                    "status": "error",
                    "error": "File path must be within active project",
                    "error_code": "PATH_OUTSIDE_PROJECT",
                    "message": f"File path '{path}' is not within active project '{active_project}'",
                    "suggestion": f"Use path: projects/{active_project}/<file_path>",
                    "active_project": active_project,
                    "file_path": path
                }, status_code=400)

        if not os.path.exists(path):
            return JSONResponse({"status": "error", "message": f"File not found: {path}"}, status_code=404)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return JSONResponse({
            "status": "success",
            "path": path,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }, status_code=200)

    except Exception as e:
        log_message(f"[Reader] Error: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, status_code=500)


@router.post("/update-file", dependencies=[Depends(verify_token)])
def update_file_api(path: str = Body(...), content: str = Body(...)):
    """
    Create or update a file with exact content.
    
    Direct file write — creates or updates a file with exact content, without AI reasoning.
    Ideal for cases when you already have full file content ready.
    
    📌 DECISION RULE:
    - Use /update-file when you want to create or replace a file with known content  
    - Use /execute when you need AI to reason, refactor, or generate code automatically
    
    ⚠️ REQUIREMENTS:
    - Active project must be set (returns 400 if not)
    - Both path and content fields are REQUIRED
    - Relative paths are automatically prefixed with the active project directory
    - Empty content ("") clears the file (use /execute for file deletion)
    
    ⚠️ REDIRECT BEHAVIOR:
    - Explicit natural-language edit commands targeting exact file content (e.g., "update file X with Y") are redirected here from /execute  
    - Commands like "create file X with ..." or "replace file Y content with ..." are also handled here directly  
    - This ensures safe, deterministic file updates without AI misinterpretation
    
    📦 FORMAT: {"path": "file.py", "content": "your code"}  
    Optional plain-text body mode exists but is rarely needed. JSON format is recommended.  
    File paths must be within the active project root for safety.
    
    🧪 EXAMPLES:
    - {"path": "utils/logger.py", "content": "def log(): pass"}  
    - {"path": "config.json", "content": "{\"debug\": true}"}  
    - {"path": "data/cache.tmp", "content": ""}   # Clears file content
    
    🧭 NOTES:
    - Returns HTTP 200 on success, 400 on invalid path/missing parameters, 403 on protected directories
    - Does not perform refactoring or AI-driven edits (use /execute for that)  
    - Fully integrated with CPL redirection layer for safe file handling
    
    Args:
        path: File path (relative paths auto-prefixed with active project)
        content: Exact file content to write (empty string '' clears file)
    
    Returns:
        File operation result with status
        
    Error Responses:
        - 400: Invalid request (missing path/content or inactive project)
        - 400: NO_ACTIVE_PROJECT - No active project set
        - 400: PATH_OUTSIDE_PROJECT - Path not in active project
        - 403: Protected directory access denied (core/, api/, utils/)
    """
    from core.context_manager import context_manager
    
    if not path:
        return JSONResponse({
            "status": "error",
            "error": "file_path parameter is required"
        }, status_code=400)
    
    # ✅ TASK 8.4: Enforce active project requirement
    active_project = context_manager.get_project()
    
    if not active_project:
        log_message(f"[SECURITY] File operation blocked: No active project set")
        return JSONResponse({
            "status": "error",
            "error": "No active project set",
            "error_code": "NO_ACTIVE_PROJECT",
            "message": "You must set an active project before performing file operations",
            "suggestion": "Use POST /projects/set-active/{project_name} to set active project",
            "file_path": path
        }, status_code=400)
    
    # ✅ TASK 8.4: Ensure path is within active project
    # Normalize path separators
    normalized_path = path.replace("\\", "/")
    
    if not normalized_path.startswith(f"projects/{active_project}/"):
        # Auto-prefix if not already prefixed with projects/
        if not normalized_path.startswith("projects/"):
            path = os.path.join("projects", active_project, path)
            log_message(f"[PROTECTION] Auto-prefixed path to active project: {path}")
        else:
            # Path is in different project - block it
            log_message(f"[SECURITY] File operation blocked: Path not in active project")
            return JSONResponse({
                "status": "error",
                "error": "File path must be within active project",
                "error_code": "PATH_OUTSIDE_PROJECT",
                "message": f"File path '{path}' is not within active project '{active_project}'",
                "suggestion": f"Use path: projects/{active_project}/<file_path>",
                "active_project": active_project,
                "file_path": path
            }, status_code=400)
    
    # Continue with update_file() call
    return update_file(path, content)


@router.get("/list-files")
def list_files(directory: str = None):
    """
    Get a recursive list of project files starting from a given directory.
    ✅ TASK 8.6: Defaults to active project when no directory specified
    Provides structured visibility into project contents for ChatGPT Apps.
    """
    try:
        # ✅ TASK 8.6 FIX: Defensive check for None, ".", "", "./" (handles all edge cases)
        # This handles: missing params, cached schema defaults, empty strings, current dir notations
        if directory in (None, ".", "", "./"):
            from core.context_manager import context_manager
            active_project = context_manager.get_project()
            
            if active_project:
                directory = f"projects/{active_project}"
                log_message(f"[List Files] Auto-detected active project: {active_project}")
            else:
                directory = "."  # Fallback to current directory
                log_message(f"[List Files] No active project, using current directory")
        
        # ✅ TASK 8.6 FIX 2: Path normalization for bare project names
        # If directory is just a project name (not already prefixed), check if project exists
        elif directory and not directory.startswith(("projects/", "/", "\\", ".", "core/", "api/", "utils/")):
            # Check if this looks like a project name and the project exists
            potential_project_path = os.path.join("projects", directory)
            if os.path.exists(potential_project_path) and os.path.isdir(potential_project_path):
                directory = potential_project_path
                log_message(f"[List Files] Normalized bare project name: {directory}")
        
        # Convert to absolute path for safety
        base_path = os.path.abspath(directory)
        project_root = os.getcwd()
        
        # Security check: prevent traversal outside project
        if not base_path.startswith(project_root):
            return JSONResponse({
                "status": "error",
                "message": "Access denied: directory is outside project root",
                "timestamp": datetime.now().isoformat()
            }, status_code=403)
        
        # Collect files recursively
        files_list = []
        for root, dirs, files in os.walk(base_path):
            # Filter out hidden directories and common excludes
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            for file in files:
                if not file.startswith('.'):  # Skip hidden files
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, project_root)
                    files_list.append(relative_path)
        
        log_message(f"[List Files] Retrieved {len(files_list)} files from {directory}")
        
        return JSONResponse({
            "status": "success",
            "directory": directory,
            "files": files_list,
            "count": len(files_list),
            "timestamp": datetime.now().isoformat()
        }, status_code=200)
        
    except Exception as e:
        log_message(f"[List Files] Error: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Failed to list files: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, status_code=500)

