"""
API Schemas - Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Memory Schemas
# ============================================================================

class MemoryResponse(BaseModel):
    """Response model for complete project memory."""
    project_name: str
    created_at: str
    last_updated: str
    actions: List[Dict[str, Any]]
    semantic_context: Dict[str, Any]
    documentation: Dict[str, Any]
    version: str


class MemoryUpdateRequest(BaseModel):
    """Request model for memory update."""
    force_reanalysis: bool = Field(
        default=False,
        description="Force re-analysis even if recently analyzed"
    )


class MemoryUpdateResponse(BaseModel):
    """Response model for memory update."""
    success: bool
    message: str
    context: Dict[str, Any]
    analyzed_at: Optional[str]


class ContextResponse(BaseModel):
    """Response model for AI context."""
    project_name: str
    description: Optional[str] = None
    tech_stack: List[str] = []
    confidence: float = 0.0
    cached: bool = False  # ✅ TASK 8.10.1.1: Always False (no caching)
    # LLM format fields
    context_string: Optional[str] = None
    recent_focus: Optional[str] = None
    error_patterns: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    # Detailed format fields
    keywords: Optional[List[str]] = None
    activity: Optional[Dict[str, Any]] = None
    last_analyzed: Optional[str] = None
    # ✅ TASK 8.9.1: Add README fields for summary/detailed/llm context responses
    readme_preview: Optional[str] = None   # For summary format (first 500 chars)
    readme_content: Optional[str] = None   # For detailed and LLM formats (up to 2000 chars)


# ============================================================================
# Documentation Schemas
# ============================================================================

class ProjectDocsResponse(BaseModel):
    """Response model for project documentation."""
    project_name: str
    readme_exists: bool
    readme_content: Optional[str]
    semantic_section: str
    last_updated: Optional[str]


class DocsUpdateRequest(BaseModel):
    """Request model for documentation update."""
    force_update: bool = Field(
        default=False,
        description="Force update even if recently updated"
    )
    sections_to_include: List[str] = Field(
        default=["overview", "tech_stack", "activity"],
        description="Sections to include in README"
    )


class DocsUpdateResponse(BaseModel):
    """Response model for documentation update."""
    success: bool
    message: str
    readme_updated: bool
    sections_added: List[str]
    updated_at: str


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Response model for errors."""
    detail: str


# ============================================================================
# Git & Commit Schemas
# ============================================================================

class CommitRequest(BaseModel):
    """Request model for Git commit operations."""
    message: str
    project: Optional[str] = None  # 🔒 TASK 1 FIX: No default - require explicit project


class FormatCommitRequest(BaseModel):
    """Request model for formatted commit messages."""
    message: str
    commit_type: str = "feat"


class UserMemoryRequest(BaseModel):
    """Request model for user memory notes."""
    notes: str = Field(..., max_length=300, description="Project rules and notes (max 300 chars). Can include project-specific rules, guidelines, reminders, or context hints.")


# ============================================================================
# Execute Schemas
# ============================================================================

class ExecBody(BaseModel):
    """Request model for /execute endpoint."""
    # Primary fields (ChatGPT/GPT Actions format)
    task: Optional[str] = None  # Alternative to 'prompt'
    commit: bool = True  # Auto-commit flag
    
    # Legacy/Alternative fields (direct Aider format)
    prompt: Optional[str] = None  # Alternative to 'task'
    instruction: Optional[str] = None  # Another alternative
    
    # Optional fields
    project: str = "default"
    model: str = "gpt-4o-mini"
    files: List[str] = []
    
    # Validation: at least one of task/prompt/instruction must be provided
    model_config = ConfigDict(extra="ignore")  # Ignore unknown fields instead of erroring
