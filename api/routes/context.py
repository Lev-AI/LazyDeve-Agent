"""
Context API Routes - Expose Task 8.9 context functionality
✅ TASK 8.9.1: Dedicated context endpoints for ChatGPT integration
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from api.schemas import ContextResponse, ErrorResponse, UserMemoryRequest
from api.dependencies import validate_project_exists
from core.ai_context import get_project_context_summary
from core.basic_functional import log_message

# Create router with /api/v1/context prefix
router = APIRouter(
    prefix="/api/v1/context",
    tags=["context"],
    responses={404: {"model": ErrorResponse}}
)


@router.get("/summary/{project_name}", response_model=ContextResponse)
async def get_summary_context(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Get AI-ready context summary (includes README preview up to 500 chars).
    
    ✅ TASK 8.9.1: Dedicated summary context endpoint
    
    **Returns:**
    - Project description
    - Tech stack
    - Recent focus
    - README preview (500 chars max)
    - Confidence score
    - Cache status
    """
    try:
        context = get_project_context_summary(project_name, format="summary")
        log_message(f"[API] Retrieved summary context for {project_name}")
        return context
        
    except Exception as e:
        log_message(f"[API] ERROR: Error getting summary context for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving context: {str(e)}"
        )


@router.get("/detailed/{project_name}", response_model=ContextResponse)
async def get_detailed_context(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Get detailed AI context (includes README content up to 2000 chars).
    
    ✅ TASK 8.9.1: Dedicated detailed context endpoint
    
    **Returns:**
    - Full project description
    - Tech stack and keywords
    - Activity summary
    - README content (2000 chars max)
    - Error patterns
    - AI suggestions
    - Confidence score
    """
    try:
        context = get_project_context_summary(project_name, format="detailed")
        log_message(f"[API] Retrieved detailed context for {project_name}")
        return context
        
    except Exception as e:
        log_message(f"[API] ERROR: Error getting detailed context for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving context: {str(e)}"
        )


@router.get("/llm/{project_name}", response_model=ContextResponse)
async def get_llm_context(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Get LLM-optimized context (README prepended to context_string).
    
    ✅ TASK 8.9.1: Dedicated LLM context endpoint
    
    **Returns:**
    - context_string (README prepended + memory data)
    - Tech stack
    - Description
    - Recent focus
    - Error patterns
    - README content (2000 chars max, separate field)
    - AI suggestions
    - Confidence score
    
    **Note:** This format is optimized for LLM selector and Aider prompts.
    README is prepended at the top of context_string for maximum visibility.
    """
    try:
        context = get_project_context_summary(project_name, format="llm")
        log_message(f"[API] Retrieved LLM context for {project_name}")
        return context
        
    except Exception as e:
        log_message(f"[API] ERROR: Error getting LLM context for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving context: {str(e)}"
        )


@router.get("/full/{project_name}", response_model=Dict[str, Any])
async def get_full_context(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Get unified full context (context_full.json structure).
    
    ✅ TASK 8.10.1.1: Unified context endpoint
    
    **Returns:**
    - Complete unified context structure
    - All memory sources merged
    - README preview (configurable via config.json["readme_chars"], default: 1400 chars) always included
    """
    try:
        from core.context_full import generate_full_context
        context = generate_full_context(project_name)
        log_message(f"[API] Retrieved full context for {project_name}")
        return context
    except Exception as e:
        log_message(f"[API] ERROR: Error getting full context for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving full context: {str(e)}"
        )


@router.post(
    "/{project_name}/user-memory",
    openapi_extra={
        "x-openai-triggers": [
            "add note",
            "remember this",
            "save to memory",
            "add project note",
            "update context memory"
        ]
    }
)
async def update_user_memory(
    request: UserMemoryRequest,
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Save project rules and notes to project context memory.
    
    ✅ TASK 8.10.1.1: User memory endpoint
    ✅ MCP-ready: Direct endpoint for MCP server integration (Task 10)
    
    **Purpose:**
    Add or update persistent project rules and notes. Can include:
    - Project-specific rules (e.g., "Always use TypeScript", "No console.log in production")
    - Development guidelines and best practices
    - Important reminders and context hints
    
    Notes are stored in config.json and included in the unified context structure
    (context_full.json) for ChatGPT.
    
    **When to use:**
    - User requests to "add a note", "save a note", "remember this", "add project rule", or "add persistent note"
    - Store project-specific rules, guidelines, or constraints
    - Store important reminders, priorities, or context hints for the project
    - Maximum 300 characters (automatically truncated if longer)
    
    **Request Format:**
    POST /api/v1/context/{project_name}/user-memory
    Body: {"notes": "Your note text here (max 300 chars)"}
    
    **Parameters:**
    - project_name (path): Project name (e.g., "my_project")
    - notes (body): User note text (max 300 chars, automatically truncated)
    
    **Returns:**
    - status: "success" or "error"
    - message: Status message
    - notes: Saved note text (truncated to 300 chars)
    
    **Example:**
    POST /api/v1/context/test_project/user-memory
    Body: {"notes": "Focus on memory optimization before adding new features"}
    
    **Note:** This endpoint writes directly to config.json. Notes are included in
    context_full.json and available to ChatGPT via GET /api/v1/context/full/{project}.
    """
    try:
        from core.context_manager import save_user_notes
        
        success = save_user_notes(project_name, request.notes)
        if success:
            return {
                "status": "success",
                "message": f"User notes updated for {project_name}",
                "notes": request.notes[:300]  # Return truncated version
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save user notes"
            )
    except Exception as e:
        log_message(f"[API] ERROR: Error updating user memory for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user memory: {str(e)}"
        )


@router.get("/debug/{project_name}")
async def get_context_debug(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Debug endpoint to inspect context loading status.
    
    ✅ TASK 8.10.1.1: Cache removed - shows context loading status only
    
    **Returns:**
    - README loading status
    - Encoding information
    - Memory validation status
    """
    try:
        from core.context_manager import load_context
        from core.memory_utils import load_memory
        
        # Check session_context
        session_context = load_context(project_name)
        readme_loaded = session_context.get("metadata", {}).get("readme_loaded", False)
        readme_content = session_context.get("metadata", {}).get("readme_content", "")
        readme_length = len(readme_content) if readme_content else 0
        readme_corrupted = readme_content.count('\ufffd') if readme_content else 0
        
        # Check memory
        memory = load_memory(project_name)
        has_semantic_context = bool(memory.get("semantic_context", {}))
        
        # ✅ TASK 8.10.1.1: Cache removed - return empty cache status
        cache_status = {}  # No cache exists
        
        return {
            "project_name": project_name,
            "readme_status": {
                "loaded": readme_loaded,
                "length": readme_length,
                "corrupted_chars": readme_corrupted,
                "corruption_percent": (readme_corrupted / readme_length * 100) if readme_length > 0 else 0,
                "has_content": bool(readme_content)
            },
            "memory_status": {
                "exists": bool(memory),
                "has_semantic_context": has_semantic_context
            },
            "cache_status": cache_status
        }
        
    except Exception as e:
        log_message(f"[API] ERROR: Error getting debug info for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving debug info: {str(e)}"
        )

