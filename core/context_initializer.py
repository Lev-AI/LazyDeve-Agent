"""
Context Initializer - Systematic context initialization and validation
✅ TASK 8.9: Unified context initialization (merged from Task 8.12)
✅ TASK 8.10 COMPATIBILITY: Prepares for memory maintenance
✅ TASK 8.11 COMPATIBILITY: Prepares for SQLite indexing
✅ TASK 9 COMPATIBILITY: Prepares for RAG integration
"""

import logging
from typing import Dict, Any, Optional
from core.basic_functional import log_message
from core.context_manager import context_manager, load_context, save_context
from core.context_sync import load_snapshot, cache_sync
from core.memory_utils import load_memory
from core.ai_context import ProjectContextProvider
from datetime import datetime


def read_readme_safely(readme_path: str) -> str:
    """
    Read README with multiple encoding fallbacks.
    ✅ TASK 8.9.2: Handles Windows encoding issues
    
    Args:
        readme_path: Path to README.md file
        
    Returns:
        README content as UTF-8 string, or empty string if all encodings fail
    """
    encodings = ["utf-8", "utf-8-sig", "cp1252", "cp1255", "latin-1"]  # ✅ Added cp1255 for Hebrew support
    
    for encoding in encodings:
        try:
            with open(readme_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            
            # Validate it's not all replacement characters (corrupted)
            if content and len(content) > 0:
                # ✅ TASK 8.9.2: Dynamic corruption threshold (max 3 replacement chars)
                replacement_count = content.count('\ufffd')  # Unicode replacement char
                if replacement_count <= 3:  # Allow up to 3 replacement characters
                    # Convert to UTF-8 if needed
                    if encoding != "utf-8":
                        content = content.encode("utf-8", errors="replace").decode("utf-8")
                    log_message(f"[ContextInit] ✅ README read with {encoding} encoding ({len(content)} chars)")
                    return content
        except (UnicodeDecodeError, LookupError, IOError) as e:
            log_message(f"[ContextInit] ⚠️ Failed to read README with {encoding}: {e}")
            continue
    
    log_message(f"[ContextInit] ❌ Failed to read README with all encoding attempts")
    return ""


def initialize_context_on_start(project_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Initialize project context when agent starts or project is selected.
    
    ✅ TASK 8.9: Systematic context initialization
    ✅ TASK 8.9 PART 2: README/memory startup loading with checksum-based updates
    ✅ TASK 8.12 MERGED: Context initialization at startup
    
    This function:
    1. Loads and validates context, snapshot, and memory
    2. Loads README.md content (for ChatGPT queries) - checksum-based caching
    3. Syncs and validates schema versions
    4. Warms up context cache (5-min TTL)
    5. Detects schema mismatches
    6. Prepares context for ChatGPT queries
    
    Args:
        project_name: Project name (optional, uses active project)
    
    Returns:
        dict: Initialized context or None if error
    """
    try:
        # Get active project
        if not project_name:
            project_name = context_manager.get_project()
        
        if not project_name:
            logging.info("[ContextInit] No active project selected.")
            return None
        
        log_message(f"[ContextInit] Initializing context for: {project_name}")
        
        # 1. Load and normalize context
        context = load_context(project_name)
        
        # 2. Load snapshot
        snapshot = load_snapshot(project_name)
        
        # 3. Load memory (for semantic context)
        try:
            memory = load_memory(project_name)
        except Exception as mem_error:
            log_message(f"[ContextInit] ⚠️ Could not load memory: {mem_error}")
            memory = {}
        
        # 4. ✅ TASK 8.9 PART 2: Load README.md content with checksum-based caching
        import os
        import hashlib
        
        readme_path = f"projects/{project_name}/README.md"
        readme_content = None
        
        try:
            if os.path.exists(readme_path):
                # ✅ TASK 8.9.2: Use safe README reader with encoding fallbacks
                readme_content = read_readme_safely(readme_path)
                if not readme_content:
                    log_message(f"[ContextInit] ⚠️ README.md is empty or unreadable for {project_name}")
                
                # Calculate current checksum
                readme_checksum = hashlib.md5(readme_content.encode()).hexdigest()
                
                # Initialize metadata if needed
                if "metadata" not in context:
                    context["metadata"] = {}
                
                # Get stored checksum from context
                stored_checksum = context.get("metadata", {}).get("readme_checksum")
                
                # Check if README changed since last load
                if stored_checksum != readme_checksum:
                    # README changed - update metadata
                    context["metadata"]["readme_content"] = readme_content[:5000]  # Limit to 5KB for token optimization
                    context["metadata"]["readme_checksum"] = readme_checksum
                    context["metadata"]["readme_loaded"] = True
                    context["metadata"]["readme_last_updated"] = datetime.now().isoformat() + "Z"
                    
                    # ✅ Save to session_context.json so it persists
                    save_context(project_name, context)
                    log_message(f"[ContextInit] ✅ README.md loaded and cached ({len(readme_content)} chars, checksum: {readme_checksum[:8]}...)")
                    
                    # ✅ TASK 8.9.1 FIX: Invalidate ProjectContextProvider cache when README is loaded/updated
                    try:
                        from core.ai_context import invalidate_project_cache
                        invalidate_project_cache(project_name)
                        log_message(f"[ContextInit] ✅ Invalidated context cache for {project_name} (README loaded/updated)")
                    except Exception as invalidation_error:
                        log_message(f"[ContextInit] ⚠️ Failed to invalidate context cache: {invalidation_error}")
                else:
                    # README unchanged - use cached version from context
                    readme_content = context.get("metadata", {}).get("readme_content", "")
                    log_message(f"[ContextInit] ✅ README.md unchanged, using cached version")
                    if "metadata" not in context:
                        context["metadata"] = {}
                    context["metadata"]["readme_loaded"] = True
                    
                    # ✅ TASK 8.9.1 FIX: Invalidate cache on first load (even if README unchanged) to ensure README is in cache
                    # This handles the case where cache was created before Task 8.9
                    try:
                        from core.ai_context import invalidate_project_cache
                        invalidate_project_cache(project_name)
                        log_message(f"[ContextInit] ✅ Invalidated context cache for {project_name} (ensuring README in cache)")
                    except Exception as invalidation_error:
                        log_message(f"[ContextInit] ⚠️ Failed to invalidate context cache: {invalidation_error}")
            else:
                log_message(f"[ContextInit] ⚠️ README.md not found for {project_name}")
                if "metadata" not in context:
                    context["metadata"] = {}
                context["metadata"]["readme_loaded"] = False
                context["metadata"]["readme_checksum"] = None
        except Exception as readme_error:
            log_message(f"[ContextInit] ⚠️ Could not load README.md: {readme_error}")
            if "metadata" not in context:
                context["metadata"] = {}
            context["metadata"]["readme_loaded"] = False
        
        # 5. ✅ TASK 8.9: Sync and validate schema versions
        context_version = context.get("schema_version", "1.0")
        snapshot_version = snapshot.get("version", "1.0")
        
        # Ensure metadata exists
        if "metadata" not in context:
            context["metadata"] = {}
        
        if context_version != snapshot_version:
            log_message(f"[ContextInit] ⚠️ Schema version mismatch: context={context_version}, snapshot={snapshot_version}")
            context["metadata"]["schema_mismatch"] = True
            context["metadata"]["snapshot_version"] = snapshot_version
        else:
            context["metadata"]["schema_mismatch"] = False
        
        # ✅ TASK 8.10.1.1: Removed cache warm-up - context is always generated fresh
        # No cache to warm up - context generation is lightweight and always fresh
        log_message(f"[ContextInit] ✅ Context ready (no cache warm-up needed)")
        
        # ✅ TASK 8.10.1.1 PHASE 6: Generate and save context_full.json for validation
        # This ensures context_full.json is created when:
        # - Agent starts (via initialize_context_on_start)
        # - Project is selected (via initialize_context_on_start)
        # After TASK 8.10.1.2: get_context() will call generate_full_context() internally, so file will also be updated
        # Direct API calls: /api/v1/context/full/{project} already calls generate_full_context() directly
        try:
            from core.context_full import generate_full_context
            generate_full_context(project_name)  # This will save context_full.json to disk
            log_message(f"[ContextInit] ✅ Generated context_full.json for {project_name}")
        except Exception as context_full_error:
            log_message(f"[ContextInit] ⚠️ Failed to generate context_full.json: {context_full_error}")
            # Non-critical - continue even if generation fails
        
        # ✅ TASK 8.10.1.3: Auto-populate semantic context (same pattern as context_full.json)
        # This ensures semantic context fields are populated for ChatGPT
        try:
            from core.memory_processor import analyze_project_context, update_memory_context
            from core.memory_utils import load_memory
            
            memory = load_memory(project_name)
            semantic_context = memory.get("semantic_context", {})
            actions = memory.get("actions", [])
            actions_count = len(actions)
            last_analyzed_count = semantic_context.get("analyzed_actions_count", 0)
            
            # Change-based check (no time cooldown):
            # - If empty/null → always run
            # - If actions increased by 10+ → run
            # - Otherwise → skip
            if not semantic_context.get("description") or (actions_count - last_analyzed_count > 10):
                log_message(f"[ContextInit] Auto-populating semantic context for {project_name} (actions: {actions_count}, last: {last_analyzed_count})")
                context = analyze_project_context(project_name)
                update_memory_context(project_name, context)
                log_message(f"[ContextInit] ✅ Auto-populated semantic context for {project_name}")
            else:
                log_message(f"[ContextInit] Semantic context up-to-date for {project_name} (skipping analysis)")
        except Exception as semantic_error:
            log_message(f"[ContextInit] ⚠️ Failed to auto-populate semantic context: {semantic_error}")
            # Non-critical - continue even if auto-population fails
        
        # 7. ✅ TASK 8.9: Sync snapshot cache (ensure consistency)
        try:
            cache_sync(project_name, force=False)
            log_message(f"[ContextInit] ✅ Snapshot cache synced")
        except Exception as sync_error:
            log_message(f"[ContextInit] ⚠️ Snapshot cache sync failed: {sync_error}")
        
        # 8. Build initialization summary
        init_summary = {
            "project": project_name,
            "context_loaded": True,
            "snapshot_loaded": True,
            "memory_loaded": bool(memory),
            "readme_loaded": context.get("metadata", {}).get("readme_loaded", False),
            "schema_version": context_version,
            "snapshot_version": snapshot_version,
            "schema_mismatch": context.get("metadata", {}).get("schema_mismatch", False),
            "cache_warmed": True,
            "last_commit": snapshot.get("last_commit"),
            "last_run": snapshot.get("last_run"),
            "status": snapshot.get("status", "unknown")
        }
        
        log_message(f"[ContextInit] ✅ Context initialized for {project_name}")
        logging.info(f"[ContextInit] Summary: {init_summary}")
        
        return context
        
    except Exception as e:
        log_message(f"[ContextInit] ❌ Failed to initialize context: {e}")
        logging.error(f"[ContextInit] Error: {e}")
        return None


def initialize_context_on_project_switch(project_name: str) -> Optional[Dict[str, Any]]:
    """
    Initialize context when project is switched.
    
    ✅ TASK 8.9: Context initialization on project switch
    
    Args:
        project_name: New active project name
    
    Returns:
        dict: Initialized context or None if error
    """
    return initialize_context_on_start(project_name)

