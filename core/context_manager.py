"""
context_manager.py
------------------
Session Context Manager for LazyDeve Agent.
Handles all session context logic independently from basic_functional.py.

All comments and docstrings are in English.
"""

import os
import json
import datetime
import logging
import threading
from typing import Dict, Any, Optional

# ===============================
# Context Manager Singleton
# ===============================

class ContextManager:
    """
    Thread-safe Singleton-based context manager to handle the current active project.
    Task 7.7.7 — Convert Global State to Singletons
    Task 7.7.7b — Thread-Safe ContextManager (Lock Integration)
    """
    
    _instance = None
    _initialized = False
    _lock = threading.Lock()  # Class-level lock for singleton creation
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.current_project = None
            self.project_contexts = {}  # Cache for project contexts
            self._instance_lock = threading.Lock()  # Instance-level lock for operations
            self._initialized = True
    
    def set_project(self, name: str) -> None:
        """Set the current active project (thread-safe)."""
        with self._instance_lock:
            self.current_project = name
            # Clear context cache when switching projects
            if name not in self.project_contexts:
                self.project_contexts[name] = {}
    
    def get_project(self) -> Optional[str]:
        """Get the current active project name (thread-safe read)."""
        with self._instance_lock:
            return self.current_project
    
    def get_project_context(self, project_name: str = None) -> dict:
        """Get context for a specific project or current project (thread-safe)."""
        with self._instance_lock:
            if project_name is None:
                project_name = self.current_project
            
            if not project_name:
                return {}
            
            # Return cached context if available
            if project_name in self.project_contexts:
                return self.project_contexts[project_name]
            
            # Load context from file
            try:
                context = load_context(project_name)
                self.project_contexts[project_name] = context
                return context
            except Exception:
                return {}
    
    def update_project_context(self, project_name: str, context_data: dict) -> bool:
        """Update context for a specific project (thread-safe)."""
        with self._instance_lock:
            try:
                success = save_context(project_name, context_data)
                if success:
                    self.project_contexts[project_name] = context_data
                return success
            except Exception:
                return False
    
    def clear_cache(self, project_name: str = None) -> None:
        """Clear context cache for a project or all projects (thread-safe)."""
        with self._instance_lock:
            if project_name:
                self.project_contexts.pop(project_name, None)
            else:
                self.project_contexts.clear()
    
    def get_active_project_context(self) -> Optional[str]:
        """Get the active project context (thread-safe, for compatibility with system_protection.py)."""
        with self._instance_lock:
            return self.current_project

# Global singleton instance
context_manager = ContextManager()

# ===============================
# Session Context Manager (Legacy Functions)
# ===============================

def get_project_context_path(project: str) -> str:
    """
    Get the path to session_context.json for a project.
    Works with both old structure (backward compatibility) and new .lazydeve/ structure.
    
    Args:
        project (str): Name of the project
        
    Returns:
        str: Path to session_context.json
    """
    project_path = os.path.join("projects", project)
    
    # Check for new structure (.lazydeve/)
    lazydeve_context_path = os.path.join(project_path, ".lazydeve", "session_context.json")
    if os.path.exists(lazydeve_context_path):
        return lazydeve_context_path
    
    # Fall back to old structure
    old_context_path = os.path.join(project_path, "session_context.json")
    return old_context_path


def get_project_context_dir(project: str) -> str:
    """
    Get the directory where session_context.json should be stored.
    Uses new .lazydeve/ structure for new projects, old structure for existing ones.
    
    Args:
        project (str): Name of the project
        
    Returns:
        str: Directory path for session_context.json
    """
    project_path = os.path.join("projects", project)
    
    # Check if project uses new structure
    lazydeve_path = os.path.join(project_path, ".lazydeve")
    if os.path.exists(lazydeve_path):
        return lazydeve_path
    
    # Fall back to project root for old structure
    return project_path

def load_context(project: str) -> dict:
    """
    Load and normalize session context for a project.
    
    ✅ TASK 8.8 FIX: Canonical schema with full normalization
    ✅ TASK 8.11 COMPATIBILITY: SQLite-ready structure (fits in metadata JSON)
    ✅ TASK 9 COMPATIBILITY: RAG-ready (fully serializable, consistent types)
    ✅ FUTURE-PROOF: Schema versioning for migrations
    
    Schema Design Principles:
    1. Versioned: Includes schema version for migration tracking
    2. Type-Safe: All fields have consistent types (no None ambiguity)
    3. RAG-Ready: Fully JSON-serializable, no missing keys
    4. SQLite-Compatible: Structure fits in metadata JSON column
    5. Unified: Aligns with snapshot, commits, events versioning
    
    Args:
        project (str): Name of the project to load context for.
        
    Returns:
        dict: Normalized context with canonical schema
    """
    # ✅ CANONICAL SCHEMA: Future-proof structure for Tasks 8.9-11, Task 9
    canonical_schema = {
        # Schema Versioning (Task 8.11, Task 9 compatibility)
        "version": "1.0",  # ✅ Schema version for migration tracking
        "schema_version": "1.0",  # ✅ Explicit schema version (matches snapshot.json pattern)
        
        # Project Identity
        "project": project,
        
        # Sync Metadata
        "last_sync": None,  # ISO timestamp or None
        "sync_status": "idle",  # "idle" | "syncing" | "stale" | "error"
        "status": "active",  # "active" | "stale" | "error"
        
        # File Tracking (for protection system integration)
        "files_updated": 0,  # Integer count
        "files_reverted": [],  # List of file paths (protection system)
        "changed_files": [],  # List of file paths (Git tracking)
        
        # Commit Tracking (aligns with commit_report.json)
        "commits_cached": 0,  # Integer count
        "commits": [],  # List of commit objects (for history)
        
        # Timestamps (ISO format for RAG/Task 9)
        "created_at": None,  # ISO timestamp or None
        "last_updated": None,  # ISO timestamp or None
        
        # Metadata (for future extensions, SQLite compatibility)
        "metadata": {}  # Flexible JSON object for extensions
    }
    
    try:
        context_path = get_project_context_path(project)
        
        if not os.path.exists(context_path):
            logging.info(f"[ContextManager] No context file found for project: {project}")
            # Return canonical schema with defaults
            canonical_schema["created_at"] = datetime.datetime.now().isoformat() + "Z"
            canonical_schema["last_updated"] = datetime.datetime.now().isoformat() + "Z"
            return canonical_schema
        
        # Load existing context
        with open(context_path, "r", encoding="utf-8") as f:
            loaded_context = json.load(f)
        
        # ✅ NORMALIZATION: Merge loaded context with canonical schema
        # This ensures all required fields exist, even if file is missing them
        normalized_context = {**canonical_schema, **loaded_context}
        
        # ✅ TYPE SAFETY: Ensure all fields match expected types
        # Fix type mismatches (e.g., if files_reverted is not a list)
        if not isinstance(normalized_context.get("files_reverted"), list):
            normalized_context["files_reverted"] = []
        
        if not isinstance(normalized_context.get("changed_files"), list):
            normalized_context["changed_files"] = []
        
        if not isinstance(normalized_context.get("commits"), list):
            normalized_context["commits"] = []
        
        if not isinstance(normalized_context.get("files_updated"), int):
            normalized_context["files_updated"] = int(normalized_context.get("files_updated", 0))
        
        if not isinstance(normalized_context.get("commits_cached"), int):
            normalized_context["commits_cached"] = int(normalized_context.get("commits_cached", 0))
        
        # ✅ SCHEMA VERSIONING: Ensure version fields exist
        if "version" not in normalized_context:
            normalized_context["version"] = "1.0"
        
        if "schema_version" not in normalized_context:
            normalized_context["schema_version"] = "1.0"
        
        # ✅ TIMESTAMP NORMALIZATION: Ensure ISO format
        if normalized_context.get("last_sync") and not isinstance(normalized_context["last_sync"], str):
            # Convert datetime objects to ISO strings if needed
            if hasattr(normalized_context["last_sync"], "isoformat"):
                normalized_context["last_sync"] = normalized_context["last_sync"].isoformat() + "Z"
        
        # Update last_updated if not present
        if not normalized_context.get("last_updated"):
            normalized_context["last_updated"] = datetime.datetime.now().isoformat() + "Z"
        
        # Ensure created_at exists
        if not normalized_context.get("created_at"):
            normalized_context["created_at"] = normalized_context["last_updated"]
        
        logging.info(f"[ContextManager] ✅ Loaded and normalized context for project: {project} (schema: {normalized_context.get('schema_version', 'unknown')})")
        return normalized_context
        
    except json.JSONDecodeError as e:
        logging.error(f"[ContextManager] Corrupted context file for {project}: {e}")
        # Return canonical schema with error status
        canonical_schema.update({
            "sync_status": "error",
            "status": "error",
            "metadata": {"error": "corrupted_file", "error_message": str(e)}
        })
        canonical_schema["created_at"] = datetime.datetime.now().isoformat() + "Z"
        canonical_schema["last_updated"] = datetime.datetime.now().isoformat() + "Z"
        return canonical_schema
        
    except Exception as e:
        logging.error(f"[ContextManager] Failed to load context for {project}: {e}")
        # Return canonical schema with error status
        canonical_schema.update({
            "sync_status": "error",
            "status": "error",
            "metadata": {"error": "load_failed", "error_message": str(e)}
        })
        canonical_schema["created_at"] = datetime.datetime.now().isoformat() + "Z"
        canonical_schema["last_updated"] = datetime.datetime.now().isoformat() + "Z"
        return canonical_schema


def save_context(project: str, data: dict) -> bool:
    """
    Overwrites the session context file, updates last_sync timestamp, and logs the save operation.
    Works with both old structure (backward compatibility) and new .lazydeve/ structure.
    
    Args:
        project (str): Name of the project to save context for.
        data (dict): Context data to save.
        
    Returns:
        bool: True if save was successful, False otherwise.
    """
    try:
        # Get the appropriate directory for this project
        context_dir = get_project_context_dir(project)
        os.makedirs(context_dir, exist_ok=True)
        
        context_path = os.path.join(context_dir, "session_context.json")
        
        # Update timestamp and project info
        data["last_sync"] = datetime.datetime.now().isoformat()
        data["project"] = project
        
        # Save to file
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"[ContextManager] Successfully saved context for project: {project}")
        return True
        
    except Exception as e:
        logging.error(f"[ContextManager] Failed to save context for {project}: {e}")
        return False


def validate_context(context: dict) -> bool:
    """
    Ensures required fields exist and checks if last_sync is not older than 24 hours.
    
    Args:
        context (dict): Context data to validate.
        
    Returns:
        bool: True if context is valid and fresh, False otherwise.
    """
    try:
        # Check required fields
        required_fields = ["last_sync", "project"]
        for field in required_fields:
            if field not in context:
                logging.warning(f"[ContextManager] Missing required field: {field}")
                return False
        
        # Check if last_sync is valid
        if not context["last_sync"]:
            logging.warning("[ContextManager] last_sync is None or empty")
            return False
        
        # Check if context is fresh (less than 24 hours old)
        try:
            last_sync = datetime.datetime.fromisoformat(context["last_sync"])
            age_hours = (datetime.datetime.now() - last_sync).total_seconds() / 3600
            
            if age_hours > 24:
                logging.info(f"[ContextManager] Context is stale (age: {age_hours:.1f} hours)")
                return False
            
            logging.info(f"[ContextManager] Context is fresh (age: {age_hours:.1f} hours)")
            return True
            
        except ValueError as e:
            logging.error(f"[ContextManager] Invalid last_sync format: {e}")
            return False
        
    except Exception as e:
        logging.error(f"[ContextManager] Context validation failed: {e}")
        return False


def get_context_summary(project: str) -> dict:
    """
    Returns a summary of the session context.
    
    Args:
        project (str): Name of the project to get summary for.
        
    Returns:
        dict: Summary with project, last_sync, commits_cached, files_cached, status.
    """
    try:
        context = load_context(project)
        
        # Determine status
        is_valid = validate_context(context)
        status = "ok" if is_valid else "stale"
        
        # Build summary
        summary = {
            "project": project,
            "last_sync": context.get("last_sync"),
            "commits_cached": context.get("commits_cached", 0),
            "files_cached": context.get("files_updated", 0),
            "status": status
        }
        
        # Add context age if last_sync exists
        if context.get("last_sync"):
            try:
                last_sync = datetime.datetime.fromisoformat(context["last_sync"])
                age_hours = (datetime.datetime.now() - last_sync).total_seconds() / 3600
                summary["context_age_hours"] = round(age_hours, 1)
            except ValueError:
                summary["context_age_hours"] = None
        
        logging.info(f"[ContextManager] Generated context summary for {project}: status={status}")
        return summary
        
    except Exception as e:
        logging.error(f"[ContextManager] Failed to get context summary for {project}: {e}")
        return {
            "project": project,
            "last_sync": None,
            "commits_cached": 0,
            "files_cached": 0,
            "status": "error",
            "error": str(e)
        }


def update_context_after_sync(project: str, sync_result: dict) -> bool:
    """
    Updates context after a GitHub sync operation.
    
    Args:
        project (str): Name of the project.
        sync_result (dict): Result from GitHub sync operation.
        
    Returns:
        bool: True if update was successful.
    """
    try:
        # Load existing context
        context = load_context(project)
        
        # Update with sync results
        context.update({
            "commits_cached": sync_result.get("commits_parsed", 0),
            "files_updated": sync_result.get("files_updated", 0),
            "commits": sync_result.get("commits", []),
            "changed_files": sync_result.get("changed_files", []),
            "sync_status": sync_result.get("status", "unknown")
        })
        
        # Save updated context
        return save_context(project, context)
        
    except Exception as e:
        logging.error(f"[ContextManager] Failed to update context after sync for {project}: {e}")
        return False


# ===============================
# Debug Entry
# ===============================

# ===============================
# Task 4: Last Active Project Persistence
# ===============================

def save_last_active_project(project_name: str) -> bool:
    """
    Persist the last active project for startup restoration.
    Task 4: Intelligent Project Defaults
    
    Args:
        project_name: Name of the project to save
        
    Returns:
        bool: True if saved successfully
    """
    try:
        # Save to dedicated file
        last_active_file = "projects/.last_active_project"
        os.makedirs("projects", exist_ok=True)
        with open(last_active_file, "w", encoding="utf-8") as f:
            f.write(project_name)
        
        # Also update root memory.json if exists
        memory_file = "memory.json"
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data["last_active_project"] = project_name
                    data["last_active_timestamp"] = datetime.datetime.now().isoformat()
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as json_error:
                logging.warning(f"[ContextManager] Could not update memory.json: {json_error}")
        
        logging.info(f"[ContextManager] ✅ Saved last active project: {project_name}")
        return True
    except Exception as e:
        logging.error(f"[ContextManager] Error saving last active project: {e}")
        return False


def restore_last_active_project() -> Optional[str]:
    """
    Restore the last active project from persistent storage.
    Called on system startup.
    Task 4: Intelligent Project Defaults
    
    Returns:
        str: Last active project name or None if not found
    """
    try:
        # Try multiple sources for last active project
        sources = [
            ("memory.json", "json"),  # Root memory file
            ("projects/.last_active_project", "text"),  # Dedicated file
        ]
        
        for source_path, source_type in sources:
            if os.path.exists(source_path):
                try:
                    if source_type == "json":
                        with open(source_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            last_project = data.get("last_active_project")
                    else:
                        with open(source_path, "r", encoding="utf-8") as f:
                            last_project = f.read().strip()
                    
                    if last_project and os.path.exists(f"projects/{last_project}"):
                        # Project exists, restore it
                        context_manager.set_project(last_project)
                        logging.info(f"[ContextManager] ✅ Restored last active project: {last_project}")
                        
                        # Load project context/memory
                        try:
                            context = load_context(last_project)
                            from core.memory_utils import load_memory
                            memory = load_memory(last_project)
                            logging.info(f"[ContextManager] ✅ Loaded context and memory for: {last_project}")
                        except Exception as load_error:
                            logging.warning(f"[ContextManager] ⚠️ Could not load context/memory: {load_error}")
                        
                        return last_project
                except Exception as e:
                    logging.warning(f"[ContextManager] Error reading {source_path}: {e}")
                    continue
        
        logging.info("[ContextManager] ⚠️ No last active project found")
        return None
        
    except Exception as e:
        logging.error(f"[ContextManager] Error restoring last active project: {e}")
        return None


if __name__ == "__main__":
    # Test the context manager
    test_project = "LazyDeve"
    
    print(f"Testing Context Manager for project: {test_project}")
    
    # Test load
    context = load_context(test_project)
    print(f"Loaded context: {context.get('status', 'unknown')}")
    
    # Test validation
    is_valid = validate_context(context)
    print(f"Context valid: {is_valid}")
    
    # Test summary
    summary = get_context_summary(test_project)
    print(f"Summary: {summary}")
    
    print("Context Manager test completed.")


def save_user_notes(project_name: str, notes: str) -> bool:
    """
    Save user notes (max 300 chars) to config.json.
    
    ✅ TASK 8.10.1.1: User memory integration
    
    Args:
        project_name: Project name
        notes: User notes (will be truncated to 300 chars)
        
    Returns:
        bool: True if successful
    """
    try:
        from core.memory_lock import safe_read_json, safe_write_json
        from core.basic_functional import log_message
        from datetime import datetime
        
        # Truncate to 300 chars
        if len(notes) > 300:
            notes = notes[:300]
        
        config_path = f"projects/{project_name}/.lazydeve/config.json"
        config = safe_read_json(config_path, {})
        
        config["user_memory"] = {
            "notes": notes,
            "last_updated": datetime.now().isoformat() + "Z"
        }
        
        safe_write_json(config_path, config, create_backup=False)
        log_message(f"[ContextManager] ✅ Saved user notes for {project_name}")
        return True
        
    except Exception as e:
        log_message(f"[ContextManager] ❌ Failed to save user notes: {e}")
        return False
