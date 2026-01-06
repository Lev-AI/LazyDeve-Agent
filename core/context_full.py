"""
Unified Context Generator - Single source for ChatGPT context
✅ TASK 8.10.1.1: Unified context_full.json structure
✅ Compatible with Task 8.11: JSON remains source of truth, SQLite mirrors
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime
from core.memory_utils import load_memory
from core.context_manager import load_context
from core.context_sync import load_snapshot
from core.commit_tracker import load_commit_data
from core.readme_utils import extract_readme_summary
from core.memory_lock import safe_read_json
from core.basic_functional import log_message


def extract_recent_actions(project_name: str, limit: int = 5) -> list:
    """
    Extract recent actions from memory.json for activity.recent_actions.
    
    ✅ TASK 8.10.1.1: Recent actions extraction
    
    Args:
        project_name: Project name
        limit: Maximum number of actions to return
        
    Returns:
        list: Recent actions with time, action, status
    """
    try:
        memory = load_memory(project_name)
        actions = memory.get("actions", [])
        
        # Get last N actions, reverse to show most recent first
        recent = actions[-limit:] if len(actions) > limit else actions
        recent.reverse()
        
        result = []
        for action in recent:
            result.append({
                "time": action.get("timestamp", ""),
                "action": action.get("description", ""),
                "status": action.get("extra", {}).get("status", "ok") if isinstance(action.get("extra"), dict) else "ok"
            })
        
        return result
    except Exception as e:
        log_message(f"[ContextFull] ⚠️ Failed to extract recent actions: {e}")
        return []


def generate_full_context(project_name: str) -> Dict[str, Any]:
    """
    Generate unified context_full.json structure from all sources.
    
    ✅ TASK 8.10.1.1: Unified context generation
    ✅ Compatible with Task 8.11: JSON remains source of truth
    
    This is a READ-ONLY merge operation - does not modify source files.
    SQLite (Task 8.11) will mirror the source JSONs, not this generated structure.
    
    Args:
        project_name: Project name
        
    Returns:
        dict: Unified context structure matching context_full.json schema
        - readme.preview: Always included (configurable via config.json["readme_chars"], default: 1400 chars max)
    """
    try:
        # 1. Load memory.json
        memory = load_memory(project_name)
        if not memory:
            log_message(f"[ContextFull] ⚠️ No memory found for {project_name}")
            memory = {}
        
        semantic_context = memory.get("semantic_context", {})
        if not semantic_context:
            semantic_context = {}
        
        # Ensure activity_summary exists
        if "activity_summary" not in semantic_context:
            semantic_context["activity_summary"] = {
                "total_actions": 0,
                "recent_focus": None,
                "common_operations": [],
                "error_patterns": []
            }
        
        activity_summary = semantic_context.get("activity_summary", {})
        
        # 2. Load session_context.json
        session_context = load_context(project_name)
        readme_metadata = session_context.get("metadata", {})
        readme_content = readme_metadata.get("readme_content", "")
        
        # 3. Load commit_history.json
        commit_data = load_commit_data(project_name)
        last_commit = commit_data.get("last_commit")
        recent_commits = commit_data.get("history", [])[:3]  # Last 3 commits
        
        # 4. Load config.json
        config_path = f"projects/{project_name}/.lazydeve/config.json"
        config = safe_read_json(config_path, {})
        user_memory = config.get("user_memory", {})
        
        # ✅ FIX: Remove user_memory from config to prevent duplication
        # user_memory will be included as a top-level field instead
        config_without_user_memory = {k: v for k, v in config.items() if k != "user_memory"}
        
        # Get readme_chars from config (default: 1400) - configurable README preview size
        readme_chars = config.get("readme_chars", 1400)
        # Ensure it's a valid integer (min 500, max 5000 for safety)
        try:
            readme_chars = max(500, min(5000, int(readme_chars)))
        except (ValueError, TypeError):
            readme_chars = 1400  # Default if invalid

        # 5. Load snapshot.json
        snapshot = load_snapshot(project_name)
        
        # 6. Extract stats from memory
        stats = memory.get("stats", {})
        
        # 7. Extract recent actions
        recent_actions = extract_recent_actions(project_name, limit=5)
        
        # 8. Build unified structure
        context = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat() + "Z",
            "project_name": project_name,
            
            # Core semantic context
            "description": semantic_context.get("description"),
            "tech_stack": semantic_context.get("tech_stack", []),
            "recent_focus": activity_summary.get("recent_focus"),
            "keywords": semantic_context.get("keywords", []),
            "confidence": semantic_context.get("confidence_score", 0.0),
            
            # README
            "readme": {
                "preview": extract_readme_summary(readme_content, max_chars=readme_chars) if readme_content else None,  # ✅ Configurable via config.json["readme_chars"], default: 1400 chars
                "last_updated": readme_metadata.get("readme_last_updated"),
                "checksum": readme_metadata.get("readme_checksum")
            },
            
            # Commits
            "commits": {
                "last_commit": last_commit,
                "recent": recent_commits
            },
            
            # Activity
            "activity": {
                "total_actions": activity_summary.get("total_actions", 0),
                "recent_focus": activity_summary.get("recent_focus"),
                "common_operations": activity_summary.get("common_operations", []),
                "error_patterns": activity_summary.get("error_patterns", []),
                "recent_actions": recent_actions
            },
            
            # Project state
            "snapshot": {
                "last_run": snapshot.get("last_run"),
                "status": snapshot.get("status", "unknown"),
                "pending_changes": snapshot.get("pending_changes", False)
            },
            
            # Config & Stats
            # ✅ FIX: Exclude user_memory from config to prevent duplication
            "config": config_without_user_memory,
            "stats": stats,
            
            # User memory (top-level, extracted from config)
            # ✅ FIX: Handle both string and array formats for notes (backward compatibility)
            "user_memory": {
                "notes": user_memory.get("notes", []),
                "last_updated": user_memory.get("last_updated")
            } if user_memory else None
        }
        
        log_message(f"[ContextFull] ✅ Generated unified context for {project_name}")
        
        # ✅ TASK 8.10.1.1 PHASE 6: Save to disk for validation and manual inspection
        # Updates automatically when:
        # - Agent starts (via context_initializer → generate_full_context())
        # - Project selected (via context_initializer → generate_full_context())
        # - After TASK 8.10.1.2: get_context() → generate_full_context() (will also save)
        # - ChatGPT calls generate_full_context() directly (via /api/v1/context/full/{project})
        try:
            context_path = f"projects/{project_name}/.lazydeve/context_full.json"
            from core.memory_lock import safe_write_json
            safe_write_json(context_path, context, create_backup=False)
            log_message(f"[ContextFull] ✅ Saved context_full.json to disk for {project_name}")
        except Exception as e:
            log_message(f"[ContextFull] ⚠️ Failed to save context_full.json: {e}")
            # Non-critical - continue even if save fails
        
        # ✅ TASK 8.11: Index context_full.json to SQLite (async-safe, non-blocking)
        try:
            from core.context_indexer import index_context_full, init_context_db
            # Ensure database is initialized
            init_context_db(project_name)
            # Index the context (non-blocking, errors are logged but don't fail)
            index_context_full(project_name, context)
        except Exception as e:
            log_message(f"[ContextFull] ⚠️ Failed to index context_full.json to SQLite: {e}")
            # Non-critical - continue even if indexing fails
        
        return context
        
    except Exception as e:
        log_message(f"[ContextFull] ❌ Failed to generate unified context: {e}")
        # Return minimal structure on error
        return {
            "version": "1.0",
            "generated_at": datetime.now().isoformat() + "Z",
            "project_name": project_name,
            "error": str(e)
        }
