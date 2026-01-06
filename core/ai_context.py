"""
AI Context Provider - Format Semantic Memory for AI Interactions
Provides AI-ready context summaries for better model selection and task execution
✅ TASK 8.10.1.1: Removed caching - always generates fresh context
✅ TASK 8.10.1.2: Uses unified context_full.json structure (single source of truth)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from core.memory_utils import load_memory
from core.basic_functional import log_message


class ProjectContextProvider:
    """
    Provides AI-ready context (always fresh, no caching).
    Singleton pattern for consistent interface.
    ✅ TASK 8.10.1.1: Removed caching - context generation is lightweight
    ✅ TASK 8.10.1.2: Uses unified context_full.json structure (single source of truth)
    """
    
    _instance: Optional['ProjectContextProvider'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # ✅ TASK 8.10.1.1: Removed all caching - always generate fresh context
        return cls._instance
    
    def get_context(
        self,
        project_name: str,
        format: str = "summary",
        use_cache: bool = True  # Parameter kept for backward compatibility, but ignored
    ) -> Dict[str, Any]:
        """
        Get AI-ready project context (unified structure, always fresh).
        
        ✅ TASK 8.10.1.2: Uses generate_full_context() internally
        ✅ Single source of truth - all formats use unified structure
        
        Args:
            project_name: Name of the project
            format: Context format ("summary", "detailed", "llm")
            use_cache: Ignored (kept for backward compatibility)
            
        Returns:
            Context dictionary (formatted based on format parameter)
        """
        try:
            from core.context_full import generate_full_context
            
            # Get unified context (single source of truth)
            full_context = generate_full_context(project_name)  # ✅ Always includes README preview (configurable, default: 1400 chars)
            
            # Format response based on requested format (for backward compatibility)
            if format == "summary":
                return {
                    "project_name": full_context["project_name"],
                    "description": full_context["description"],
                    "tech_stack": full_context["tech_stack"],
                    "recent_focus": full_context["recent_focus"],
                    "readme_preview": full_context["readme"]["preview"],
                    "confidence": full_context["confidence"],
                    "cached": False
                }
            elif format == "detailed":
                return {
                    "project_name": full_context["project_name"],
                    "description": full_context["description"],
                    "tech_stack": full_context["tech_stack"],
                    "keywords": full_context["keywords"],
                    "activity": full_context["activity"],
                    "readme_content": full_context["readme"]["preview"],  # ✅ Uses unified readme.preview (configurable)
                    "commit_report": full_context["commits"]["last_commit"],
                    "confidence": full_context["confidence"],
                    "last_analyzed": None,  # Can be added to unified structure if needed
                    "suggestions": _generate_suggestions_from_unified(full_context),
                    "cached": False
                }
            elif format == "llm":
                # Build context_string from unified data
                context_parts = []
                
                if full_context["readme"]["preview"]:
                    context_parts.append(f"README:\n{full_context['readme']['preview']}")
                
                if full_context["description"]:
                    context_parts.append(f"Project: {full_context['description']}")
                
                if full_context["tech_stack"]:
                    context_parts.append(f"Tech Stack: {', '.join(full_context['tech_stack'])}")
                
                if full_context["recent_focus"]:
                    context_parts.append(f"Current Focus: {full_context['recent_focus']}")
                
                error_patterns = full_context["activity"].get("error_patterns", [])
                if error_patterns:
                    context_parts.append(f"Recent Issues: {', '.join(error_patterns[:2])}")
                
                # Add commit info
                if full_context["commits"]["last_commit"]:
                    commit = full_context["commits"]["last_commit"]
                    commit_id = commit.get("commit_id", "unknown")
                    commit_summary = commit.get("summary", "No message")[:50]
                    files_count = len(commit.get("files_changed", []))
                    context_parts.append(f"Last Commit ({commit_id}): {commit_summary} ({files_count} files)")
                
                # Add recent commits (if available)
                recent_commits = full_context["commits"].get("recent", [])
                if len(recent_commits) > 1:
                    recent = [c.get("summary", "")[:30] for c in recent_commits[1:] if c.get("summary")]
                    if recent:
                        context_parts.append(f"Recent Commits: {', '.join(recent)}")
                
                context_string = " | ".join(context_parts)
                
                return {
                    "project_name": full_context["project_name"],
                    "context_string": context_string,
                    "tech_stack": full_context["tech_stack"],
                    "description": full_context["description"],
                    "recent_focus": full_context["recent_focus"],
                    "error_patterns": error_patterns,
                    "readme_content": full_context["readme"]["preview"],  # ✅ Uses unified readme.preview (configurable)
                    "commit_report": full_context["commits"]["last_commit"],
                    "confidence": full_context["confidence"],
                    "suggestions": _generate_suggestions_from_unified(full_context),
                    "cached": False
                }
            else:
                # Fallback to summary
                return self.get_context(project_name, format="summary", use_cache=False)
                
        except Exception as e:
            log_message(f"[AIContext] ERROR: Error generating context for {project_name}: {str(e)}")
            return {
                "project_name": project_name,
                "error": str(e),
                "cached": False
            }
    
    def invalidate(self, project_name: str) -> None:
        """
        No-op method (kept for backward compatibility).
        
        ✅ TASK 8.10.1.1: Cache removed - this method does nothing
        
        Args:
            project_name: Name of the project (ignored)
        """
        pass  # No cache to invalidate
    
    def invalidate_by_key(self, cache_key: str) -> None:
        """
        No-op method (kept for backward compatibility).
        
        ✅ TASK 8.10.1.1: Cache removed - this method does nothing
        
        Args:
            cache_key: Cache key (ignored)
        """
        pass  # No cache to invalidate
    
    def get_cache_snapshot(self, project_name: str = None) -> Dict[str, Any]:
        """
        Get cache snapshot (returns empty - no cache exists).
        
        ✅ TASK 8.10.1.1: Cache removed - returns empty snapshot
        
        Args:
            project_name: Optional project name (ignored)
            
        Returns:
            Empty dictionary (no cache exists)
        """
        return {}  # No cache to snapshot
    
    def clear_cache(self) -> None:
        """
        No-op method (kept for backward compatibility).
        
        ✅ TASK 8.10.1.1: Cache removed - this method does nothing
        """
        pass  # No cache to clear
    
    def _generate_context(self, project_name: str, format: str) -> Dict[str, Any]:
        """
        Generate AI-ready context from semantic memory, README, AND commit report.
        ✅ TASK 8.9 PHASE 3: Unified injection pipeline (memory + README)
        ✅ TASK 8.10.1: Unified injection pipeline (memory + README + commit_report)
        
        Args:
            project_name: Name of the project
            format: Context format
            
        Returns:
            Context dictionary
        """
        try:
            # 1. Load semantic memory
            memory = load_memory(project_name)
            if not memory:
                log_message(f"[AIContext] ⚠️ No memory found for {project_name}, using empty memory")
                memory = {"semantic_context": {}}
            
            semantic_context = memory.get("semantic_context", {})
            if not semantic_context:
                log_message(f"[AIContext] ⚠️ No semantic_context in memory for {project_name}, using empty context")
                semantic_context = {}
            
            # ✅ TASK 8.9.2: Validate activity_summary exists
            if "activity_summary" not in semantic_context:
                semantic_context["activity_summary"] = {
                    "total_actions": 0,
                    "recent_focus": None,
                    "common_operations": [],
                    "error_patterns": []
                }
                log_message(f"[AIContext] ⚠️ WARNING: Missing activity_summary, using defaults - memory may be inconsistent")
            
            # 2. ✅ TASK 8.9 PHASE 3: Load README from cached session_context.json
            from core.context_manager import load_context
            session_context = load_context(project_name)
            readme_content = session_context.get("metadata", {}).get("readme_content", "")
            
            # ✅ TASK 8.9.2: Validate README content is not corrupted (dynamic threshold)
            if readme_content:
                # Check for corruption markers (max 3 replacement chars allowed)
                replacement_count = readme_content.count('\ufffd')
                if replacement_count > 3:
                    log_message(f"[AIContext] ⚠️ README content appears corrupted ({replacement_count} replacement chars > 3), treating as empty")
                    readme_content = ""
                elif not isinstance(readme_content, str):
                    log_message(f"[AIContext] ⚠️ README content is not a string, converting")
                    readme_content = str(readme_content) if readme_content else ""
            
            # 3. ✅ TASK 8.10.1: Load commit data from unified commit_history.json
            #    (SAME injection method as memory/README - load at dispatch level)
            from core.commit_tracker import load_commit_data
            commit_data = {}
            commit_report = None
            commit_history = []
            
            try:
                commit_data = load_commit_data(project_name)
                commit_report = commit_data.get("last_commit")
                # Get configurable max_commits (default: 3) for recent commits
                max_commits = commit_data.get("max_commits", 3)
                commit_history = commit_data.get("history", [])[:max_commits]
            except Exception as commit_error:
                log_message(f"[AIContext] ⚠️ Could not load commit data: {commit_error}")
                # Graceful degradation - continue without commit info
            
            # 4. Dispatch into correct format generator (with README AND commit report)
            if format == "summary":
                return self._generate_summary(project_name, semantic_context, readme_content)
            elif format == "detailed":
                return self._generate_detailed(project_name, semantic_context, memory, readme_content, commit_report)
            elif format == "llm":
                return self._generate_llm_context(project_name, semantic_context, memory, readme_content, commit_report, commit_history)
            else:
                # Fallback to summary
                return self._generate_summary(project_name, semantic_context, readme_content)
                
        except Exception as e:
            log_message(f"[AIContext] ERROR: Error generating context for {project_name}: {str(e)}")
            return {
                "project_name": project_name,
                "error": str(e),
                "cached": False
            }
    
    def _generate_summary(self, project_name: str, semantic_context: Dict[str, Any], readme_content: str = "") -> Dict[str, Any]:
        """
        Generate summary context.
        ✅ TASK 8.9 PHASE 3: Includes README preview (750 chars max for token safety)
        ✅ TASK 8.10.1.1: Increased from 500 to 750 chars to include architecture section
        ✅ TASK 8.9.1 FIX: Properly handle None/empty readme_content (returns None instead of "")
        ✅ TASK 8.9.3 ENHANCEMENT: Hybrid overview + architecture extraction
        """
        # ✅ TASK 8.9.3 ENHANCEMENT: Use intelligent hybrid extraction
        # ✅ TASK 8.9.1 FIX: Handle None and empty string cases properly
        # Returns None instead of "" to match schema (Optional[str] = None)
        if readme_content and isinstance(readme_content, str) and len(readme_content) > 0:
            from core.readme_utils import extract_readme_summary  # New utility function
            readme_preview = extract_readme_summary(readme_content, max_chars=750)  # ✅ TASK 8.10.1.1: Changed from 500 to 750
        else:
            readme_preview = None
        
        return {
            "project_name": project_name,
            "description": semantic_context.get("description", f"Project: {project_name}"),
            "tech_stack": semantic_context.get("tech_stack", []),
            "recent_focus": semantic_context.get("activity_summary", {}).get("recent_focus"),
            "readme_preview": readme_preview,  # ✅ Returns None if no README (matches schema)
            "confidence": semantic_context.get("confidence_score", 0.0),
            "cached": True
        }
    
    def _generate_detailed(
        self,
        project_name: str,
        semantic_context: Dict[str, Any],
        memory: Dict[str, Any],
        readme_content: str = "",
        commit_report: Optional[Dict[str, Any]] = None  # ✅ TASK 8.10.1: Add parameter
    ) -> Dict[str, Any]:
        """
        Generate detailed context.
        ✅ TASK 8.9 PHASE 3: Includes README content (2000 chars max for deeper inspection)
        ✅ TASK 8.9.1 FIX: Properly handle None/empty readme_content (returns None instead of "")
        ✅ TASK 8.10.1: Include commit report in detailed format
        """
        activity_summary = semantic_context.get("activity_summary", {})
        
        # ✅ TASK 8.9.1 FIX: Handle None and empty string cases properly
        # Returns None instead of "" to match schema (Optional[str] = None)
        if readme_content and isinstance(readme_content, str) and len(readme_content) > 0:
            readme_content_value = readme_content[:2000]
        else:
            readme_content_value = None
        
        return {
            "project_name": project_name,
            "description": semantic_context.get("description"),
            "tech_stack": semantic_context.get("tech_stack", []),
            "keywords": semantic_context.get("keywords", []),
            "activity": {
                "total_actions": activity_summary.get("total_actions", 0),
                "recent_focus": activity_summary.get("recent_focus"),
                "common_operations": activity_summary.get("common_operations", []),
                "error_patterns": activity_summary.get("error_patterns", [])
            },
            "readme_content": readme_content_value,  # ✅ Returns None if no README (matches schema)
            "commit_report": commit_report,  # ✅ TASK 8.10.1: Include in detailed format
            "confidence": semantic_context.get("confidence_score", 0.0),
            "last_analyzed": semantic_context.get("last_analyzed"),
            "suggestions": _generate_suggestions(memory),
            "cached": True
        }
    
    def _generate_llm_context(
        self,
        project_name: str,
        semantic_context: Dict[str, Any],
        memory: Dict[str, Any],
        readme_content: str = "",
        commit_report: Optional[Dict[str, Any]] = None,  # ✅ TASK 8.10.1: Add parameter
        commit_history: Optional[List[Dict[str, Any]]] = None  # ✅ TASK 8.10.1: Add parameter
    ) -> Dict[str, Any]:
        """
        Generate LLM-optimized context (for Task 7.7.14 integration).
        ✅ TASK 8.9 PHASE 3: README prepended to context_string for maximum visibility
        ✅ TASK 8.10.1: Commit report injected (same path as memory/README)
        
        This format is designed for passing to LLM selector and Aider prompts.
        README is prepended at the top of context_string so ChatGPT sees it first.
        """
        if commit_history is None:
            commit_history = []
        
        tech_stack = semantic_context.get("tech_stack", [])
        activity_summary = semantic_context.get("activity_summary", {})
        
        # Build context string
        context_parts = []
        
        # ✅ TASK 8.9 PHASE 3: PREPEND README into main LLM context (2000 chars max)
        if readme_content:
            context_parts.append(f"README:\n{readme_content[:2000]}")
        
        description = semantic_context.get("description")
        if description:
            context_parts.append(f"Project: {description}")
        
        if tech_stack:
            context_parts.append(f"Tech Stack: {', '.join(tech_stack)}")
        
        recent_focus = activity_summary.get("recent_focus")
        if recent_focus:
            context_parts.append(f"Current Focus: {recent_focus}")
        
        error_patterns = activity_summary.get("error_patterns", [])
        if error_patterns:
            context_parts.append(f"Recent Issues: {', '.join(error_patterns[:2])}")
        
        # ✅ TASK 8.10.1: Inject commit report (same injection path as memory/README)
        if commit_report:
            commit_summary = commit_report.get("summary", "No message")[:50]
            files_count = len(commit_report.get("files_changed", []))
            commit_id = commit_report.get("commit_id", "unknown")
            context_parts.append(f"Last Commit ({commit_id}): {commit_summary} ({files_count} files)")
            
            # Add recent commits (if token budget allows)
            # Note: commit_history[0] is same as last_commit, so skip it
            if len(commit_history) > 1:
                recent = [c.get("summary", "")[:30] for c in commit_history[1:] if c.get("summary")]
                if recent:
                    context_parts.append(f"Recent Commits: {', '.join(recent)}")
        
        context_string = " | ".join(context_parts)
        
        # ✅ TASK 8.9.1 FIX: Handle None and empty string cases properly (for consistency)
        # Returns None instead of "" to match schema (Optional[str] = None)
        if readme_content and isinstance(readme_content, str) and len(readme_content) > 0:
            readme_content_value = readme_content[:2000]
        else:
            readme_content_value = None
        
        return {
            "project_name": project_name,
            "context_string": context_string,  # ✅ README + commit report now included
            "tech_stack": tech_stack,
            "description": description,
            "recent_focus": recent_focus,
            "error_patterns": error_patterns,
            "readme_content": readme_content_value,  # ✅ Returns None if no README (matches schema)
            "commit_report": commit_report,  # ✅ TASK 8.10.1: Include in response
            "confidence": semantic_context.get("confidence_score", 0.0),
            "suggestions": _generate_suggestions(memory),
            "cached": True
        }


def _generate_suggestions(memory: Dict[str, Any]) -> List[str]:
    """
    Generate AI-driven suggestions based on project state.
    
    Args:
        memory: Project memory
        
    Returns:
        List of suggestions
    """
    suggestions = []
    semantic_context = memory.get("semantic_context", {})
    
    # Check confidence
    confidence = semantic_context.get("confidence_score", 0.0)
    if confidence < 0.5:
        suggestions.append("Consider adding more development actions to improve context understanding")
    
    # Check tech stack
    tech_stack = semantic_context.get("tech_stack", [])
    if not tech_stack:
        suggestions.append("No technologies detected yet - continue development to build tech profile")
    
    # Check testing
    if "testing" not in tech_stack and "pytest" not in tech_stack:
        if "python" in tech_stack:
            suggestions.append("Consider adding tests - pytest is recommended for Python projects")
    
    # Check documentation
    documentation = memory.get("documentation", {})
    if not documentation.get("readme_last_updated"):
        suggestions.append("README can be auto-generated with semantic insights")
    
    # Check errors
    activity_summary = semantic_context.get("activity_summary", {})
    error_patterns = activity_summary.get("error_patterns", [])
    if error_patterns:
        suggestions.append(f"Address recurring errors: {error_patterns[0]}")
    
    # Check recent activity
    actions = memory.get("actions", [])
    if len(actions) > 50:
        suggestions.append("Consider reviewing project progress and planning next milestones")
    
    return suggestions[:5]  # Return top 5 suggestions


def _generate_suggestions_from_unified(full_context: Dict[str, Any]) -> List[str]:
    """
    Generate AI-driven suggestions from unified context structure.
    
    ✅ TASK 8.10.1.2: Suggestions from unified context
    
    Args:
        full_context: Unified context structure from generate_full_context()
        
    Returns:
        List of suggestions
    """
    suggestions = []
    
    # Check confidence
    confidence = full_context.get("confidence", 0.0)
    if confidence < 0.5:
        suggestions.append("Consider adding more development actions to improve context understanding")
    
    # Check tech stack
    tech_stack = full_context.get("tech_stack", [])
    if not tech_stack:
        suggestions.append("No technologies detected yet - continue development to build tech profile")
    
    # Check testing
    if "testing" not in tech_stack and "pytest" not in tech_stack:
        if "python" in tech_stack:
            suggestions.append("Consider adding tests - pytest is recommended for Python projects")
    
    # Check README
    readme = full_context.get("readme", {})
    if not readme.get("preview"):
        suggestions.append("README can be auto-generated with semantic insights")
    
    # Check errors
    activity = full_context.get("activity", {})
    error_patterns = activity.get("error_patterns", [])
    if error_patterns:
        suggestions.append(f"Address recurring errors: {error_patterns[0]}")
    
    # Check recent activity
    total_actions = activity.get("total_actions", 0)
    if total_actions > 50:
        suggestions.append("Consider reviewing project progress and planning next milestones")
    
    return suggestions[:5]  # Return top 5 suggestions


# ============================================================================
# Public API Functions (Singleton Wrappers)
# ============================================================================

def get_project_context_summary(
    project_name: str,
    format: str = "summary",
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Get AI-ready project context (singleton wrapper).
    
    Args:
        project_name: Name of the project
        format: Context format ("summary", "detailed", "llm")
        use_cache: Whether to use cached context
        
    Returns:
        Context dictionary
    """
    provider = ProjectContextProvider()
    return provider.get_context(project_name, format, use_cache)


def invalidate_project_cache(project_name: str) -> None:
    """
    Invalidate cache for a project (singleton wrapper).
    
    Args:
        project_name: Name of the project
    """
    provider = ProjectContextProvider()
    provider.invalidate(project_name)


def clear_all_context_cache() -> None:
    """Clear all cached contexts (singleton wrapper)."""
    provider = ProjectContextProvider()
    provider.clear_cache()


def get_llm_context_string(project_name: str) -> str:
    """
    Get LLM-optimized context string for Task 7.7.14 integration.
    
    Args:
        project_name: Name of the project
        
    Returns:
        Context string for LLM
    """
    context = get_project_context_summary(project_name, format="llm")
    return context.get("context_string", f"Project: {project_name}")





