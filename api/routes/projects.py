"""
Project Routes - Project management endpoints
Extracted from agent.py for Task 7 Phase 2
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from core import project_manager as pm

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/list")
def list_projects():
    """
    List all available projects in the projects/ directory.
    
    Returns:
        List of project names with count
    """
    projects = pm.list_projects()
    return {"projects": projects, "count": len(projects)}


@router.post("/create/{name}")
def create_project(name: str, description: str = None, language: str = "generic"):
    """
    Create a new project with validation.
    ✅ TASK 4.2 FIX: Single Flag GitHub Control Design
    GitHub behavior is controlled entirely by allow_github_access environment variable.
    
    Args:
        name: Project name (alphanumeric + underscore/hyphen only)
        description: Optional project description
        language: Project language/framework (default: "generic")
    
    Returns:
        Creation result with project details and GitHub status
        
    Behavior:
        - If allow_github_access=true: Automatically creates GitHub repository and pushes initial commit
        - If allow_github_access=false: Creates local Git repository only (no GitHub operations)
    """
    from core.config import allow_github_access
    
    # ✅ SIMPLIFIED: GitHub creation is automatic when allow_github_access=true
    # No create_github_repo parameter needed - single source of truth
    return pm.create_project(name, description, language, create_github_repo=allow_github_access)


@router.get("/active")
def active_project():
    """
    Get currently active project name AND context (if available).
    
    ✅ TASK 8.9.3: Returns active project + context for ChatGPT initialization
    
    **Returns:**
    - active_project: Project name (always present, backward compatible)
    - context: Full unified context structure (optional, only if project is active and context available)
    
    **Context Format:**
    - Returns full unified context structure (context_full.json format)
    - Includes: commits, activity, snapshot, config, stats, user_memory, README preview
    - ✅ TASK 8.10.1.2: Full unified structure for complete ChatGPT context
    """
    from core.project_manager import get_active_project
    from core.ai_context import get_project_context_summary
    from core.basic_functional import log_message
    
    active = get_active_project()
    
    # ✅ Always return active_project (backward compatible)
    result = {
        "active_project": active
    }
    
    # ✅ TASK 8.9.3: Add context only if project is active (optional field)
    # ✅ TASK 8.10.1.2 FIX: Return full unified context structure (not summary format)
    if active:
        try:
            # Return full unified context structure (context_full.json format)
            # This includes: commits, activity, snapshot, config, stats, user_memory
            from core.context_full import generate_full_context
            context = generate_full_context(active)
            result["context"] = context
            log_message(f"[API] ✅ Included full unified context in /projects/active response for {active}")
        except Exception as e:
            # ✅ Don't fail if context loading fails - just omit it
            # active_project still returned (backward compatible)
            log_message(f"[API] ⚠️ Could not load context for {active}: {e}")
            # Context field omitted - endpoint still works
    
    return result


@router.post("/set-active/{name}")
def set_active(name: str):
    """
    Set active project with validation AND return context.
    
    ✅ TASK 8.9.3: Returns context immediately when project changes
    
    **Args:**
        name: Project name to activate
    
    **Returns:**
        Activation result with project details and context
        
    **Context Format:**
    - Returns full unified context structure (context_full.json format)
    - Includes: commits, activity, snapshot, config, stats, user_memory, README preview
    - ✅ TASK 8.10.1.2: Full unified structure for complete ChatGPT context
    """
    from core.basic_functional import log_message
    
    result = pm.set_active_project(name)
    
    # ✅ TASK 8.9.3: Add context to response if activation successful
    # ✅ TASK 8.10.1.2 FIX: Return full unified context structure (not summary format)
    if result.get("status") == "success":
        active_project = result.get("active_project")
        if active_project:
            try:
                from core.context_full import generate_full_context
                # Return full unified context structure (context_full.json format)
                context = generate_full_context(active_project)
                result["context"] = context
                log_message(f"[API] ✅ Included full unified context in /projects/set-active response for {active_project}")
            except Exception as e:
                # ✅ Don't fail if context loading fails - just omit it
                # Activation still successful, context field omitted
                log_message(f"[API] ⚠️ Could not load context for {active_project}: {e}")
                # Context field omitted - endpoint still works
    
    return result


@router.get("/info/{name}")
def project_info(name: str):
    """
    Get detailed project information including memory and stats.
    
    Args:
        name: Project name
    
    Returns:
        Detailed project information
    """
    return pm.get_project_info(name)


@router.post("/commit")
def commit_project(message: str = "Auto commit"):
    """
    Commit and push active project changes.
    
    Args:
        message: Commit message (default: "Auto commit")
    
    Returns:
        Commit operation result
    """
    return pm.commit_project(message)


@router.post("/archive/{name}")
def archive_project_endpoint(name: str):
    """
    Archive (soft delete) a project by moving it to projects/.trash/
    Prevents archiving the currently active project.
    After archiving, if archived project was active, clears active project.
    Task 5: Safe project archivation system
    
    Args:
        name: Project name to archive
    
    Returns:
        JSONResponse with archive result and project selection prompt if needed
    """
    from core.project_manager import archive_project, list_projects
    
    result = archive_project(name)
    
    # Return appropriate HTTP status code based on result
    if result.get("status") == "error":
        error_code = result.get("error_code", "UNKNOWN_ERROR")
        status_code = 400 if error_code in ["ACTIVE_PROJECT", "INVALID_NAME"] else 404
        return JSONResponse(result, status_code=status_code)
    
    # If archive successful and requires project selection, include available projects
    if result.get("requires_project_selection"):
        available_projects = list_projects()
        result["available_projects"] = available_projects
        result["suggestion"] = "Use POST /projects/set-active/{name} to select a new active project"
    
    return JSONResponse(result, status_code=200)
