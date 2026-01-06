"""
Documentation Management API Routes
Endpoints for README generation and project docs
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from api.schemas import (
    ProjectDocsResponse,
    DocsUpdateRequest,
    DocsUpdateResponse,
    ErrorResponse
)
from api.dependencies import validate_project_exists
from core.documentation_generator import (
    generate_project_docs,
    update_readme,
    get_readme_content,
    should_update_readme,
    delete_semantic_section
)
from core.basic_functional import log_message


# Create router with prefix to avoid conflicts
router = APIRouter(
    prefix="/api/v1/projects/{project_name}/docs",
    tags=["documentation"],
    responses={404: {"model": ErrorResponse}}
)


@router.get("", response_model=ProjectDocsResponse)
async def get_project_docs(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Get project documentation including README content and semantic section.
    
    **Returns:**
    - README existence status
    - README content
    - Semantic section content
    - Last update timestamp
    """
    try:
        docs = generate_project_docs(project_name)
        readme_content = get_readme_content(project_name)
        
        from pathlib import Path
        readme_path = Path(f"projects/{project_name}/README.md")
        readme_exists = readme_path.exists()
        
        log_message(f"[API] Retrieved docs for {project_name}")
        
        return {
            "project_name": project_name,
            "readme_exists": readme_exists,
            "readme_content": readme_content,
            "semantic_section": docs.get("overview", "") + docs.get("tech_stack", "") + docs.get("activity", ""),
            "last_updated": docs.get("metadata", {}).get("generated_at")
        }
        
    except Exception as e:
        log_message(f"[API] ERROR: Error retrieving docs for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading documentation: {str(e)}"
        )


@router.post("/update", response_model=DocsUpdateResponse)
async def update_project_docs(
    request: DocsUpdateRequest,
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Update project README with semantic insights (non-destructive).
    
    **Parameters:**
    - `force_update`: Force update even if recently updated
    - `sections_to_include`: Sections to include in README
    
    **Returns:**
    - Success status
    - Update message
    - Sections added
    - Update timestamp
    """
    try:
        # Check if update needed
        if not request.force_update and not should_update_readme(project_name):
            log_message(f"[API] README for {project_name} is up-to-date")
            return {
                "success": True,
                "message": "README is already up-to-date",
                "readme_updated": False,
                "sections_added": [],
                "updated_at": ""
            }
        
        # Update README
        log_message(f"[API] Updating README for {project_name}...")
        success = update_readme(
            project_name,
            sections=request.sections_to_include,
            force=request.force_update
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update README"
            )
        
        from datetime import datetime
        updated_at = datetime.now().isoformat()
        
        log_message(f"[API] README updated for {project_name}")
        
        return {
            "success": True,
            "message": "README updated successfully",
            "readme_updated": True,
            "sections_added": request.sections_to_include,
            "updated_at": updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_message(f"[API] ERROR: Error updating docs for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating README: {str(e)}"
        )


@router.delete("/semantic-section")
async def remove_semantic_section(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, str]:
    """
    Remove auto-generated semantic section from README.
    
    **Returns:**
    - Success message
    """
    try:
        success = delete_semantic_section(project_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No semantic section found or README doesn't exist"
            )
        
        log_message(f"[API] Removed semantic section from {project_name} README")
        return {"message": f"Semantic section removed from {project_name} README"}
        
    except HTTPException:
        raise
    except Exception as e:
        log_message(f"[API] ERROR: Error removing semantic section for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing semantic section: {str(e)}"
        )


@router.get("/readme")
async def get_readme(
    project_name: str = Depends(validate_project_exists)
) -> Dict[str, Any]:
    """
    Get raw README content.
    
    **Returns:**
    - README content
    - Existence status
    """
    try:
        content = get_readme_content(project_name)
        
        if content is None:
            return {
                "project_name": project_name,
                "exists": False,
                "content": None
            }
        
        return {
            "project_name": project_name,
            "exists": True,
            "content": content
        }
        
    except Exception as e:
        log_message(f"[API] ERROR: Error reading README for {project_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading README: {str(e)}"
        )





