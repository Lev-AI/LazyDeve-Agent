"""
Memory Management API Routes
Endpoints for semantic memory operations
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from api.schemas import (
    MemoryResponse,
    MemoryUpdateRequest,
    MemoryUpdateResponse,
    ContextResponse,
    ErrorResponse
)
from api.dependencies import validate_project_exists
from core.memory_utils import load_memory
from core.memory_processor import analyze_project_context, update_memory_context
from core.ai_context import get_project_context_summary, invalidate_project_cache
from core.basic_functional import log_message


# Create router with prefix to avoid conflicts
router = APIRouter(
    prefix="/api/v1/projects/{project_name}/memory",
    tags=["memory"],
    responses={404: {"model": ErrorResponse}}
)


@router.get("", response_model=MemoryResponse)
async def get_project_memory(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Get complete project memory including semantic context.
    
    **Returns:**
    - Complete memory.json with semantic context
    - Actions history
    - Documentation metadata
    """
    try:
        memory = load_memory(project_name)
        log_message(f"[API] Retrieved memory for {project_name}")
        return memory
        
    except Exception as e:
        log_message(f"[API] ERROR: Error retrieving memory for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading memory: {str(e)}"
        )


@router.post("/update", response_model=MemoryUpdateResponse)
async def update_project_memory(
    request: MemoryUpdateRequest,
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Trigger semantic analysis and update memory context.
    
    **Parameters:**
    - `force_reanalysis`: Force re-analysis even if recently analyzed
    
    **Returns:**
    - Success status
    - Updated semantic context
    - Analysis timestamp
    """
    try:
        # ✅ TASK 8.10.1.3: Change-based check (no time cooldown)
        if not request.force_reanalysis:
            memory = load_memory(project_name)
            semantic_context = memory.get("semantic_context", {})
            actions = memory.get("actions", [])
            actions_count = len(actions)
            last_analyzed_count = semantic_context.get("analyzed_actions_count", 0)
            
            # Change-based check:
            # - If empty/null → always run
            # - If actions increased by 10+ → run
            # - Otherwise → skip (unless force_reanalysis=True)
            if semantic_context.get("description") and (actions_count - last_analyzed_count <= 10):
                log_message(f"[API] {project_name} semantic context up-to-date (actions: {actions_count}, last: {last_analyzed_count}), skipping")
                return {
                    "success": True,
                    "message": "Analysis skipped - no significant changes detected",
                    "context": semantic_context,
                    "analyzed_at": semantic_context.get("last_analyzed")
                }
        
        # Perform analysis
        log_message(f"[API] Analyzing {project_name}...")
        context = analyze_project_context(project_name)
        
        # Update memory
        success = update_memory_context(project_name, context)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update memory context"
            )
        
        # Invalidate AI context cache
        invalidate_project_cache(project_name)
        
        log_message(f"[API] Memory updated for {project_name}")
        
        return {
            "success": True,
            "message": "Semantic analysis completed",
            "context": context,
            "analyzed_at": context.get("last_analyzed")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_message(f"[API] ERROR: Error updating memory for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing project: {str(e)}"
        )


@router.get("/context", response_model=ContextResponse)
async def get_ai_context(
    project_name: str = Depends(validate_project_exists),
    format: str = "summary"
) -> Dict[str, Any]:
    """
    Get AI-ready context summary.
    
    ⚠️ **DEPRECATED**: This endpoint is deprecated. Use `/api/v1/context/{format}/{project_name}` instead:
    - `/api/v1/context/summary/{project_name}` for summary format
    - `/api/v1/context/detailed/{project_name}` for detailed format
    - `/api/v1/context/llm/{project_name}` for LLM format
    
    This endpoint will be removed in a future version.
    
    **Query Parameters:**
    - `format`: Context format (summary, detailed, llm)
    
    **Returns:**
    - AI-optimized context summary
    - Tech stack
    - Recent focus
    - AI-generated suggestions
    - Cache status (always False - no cache exists)
    """
    try:
        log_message(f"[API] ⚠️ DEPRECATED endpoint /memory/context called for {project_name} (format={format})")
        context = get_project_context_summary(project_name, format=format)
        log_message(f"[API] Retrieved AI context for {project_name} (format={format})")
        return context
        
    except Exception as e:
        log_message(f"[API] ERROR: Error getting AI context for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving context: {str(e)}"
        )


# ✅ REMOVED: /context/invalidate endpoint
# Cache was removed in TASK 8.10.1.1 Phase 5 - this endpoint is obsolete
# The invalidate_project_cache() function is now a no-op (kept for backward compatibility)


