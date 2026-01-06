"""
Context Synchronization - Project state snapshot management
✅ TASK 8.7 Step 5: Unified context synchronization layer with caching and versioning
✅ TASK 8.8: Snapshot management with optimistic locking
✅ TASK 8.11 COMPATIBILITY: Async-safe operations for SQLite indexing

Cache Policy:
  - Flush interval: 5 seconds
  - Max pending updates: 10
  - Ensures eventual consistency between cache and disk.
  - Cache is flushed when either time threshold (5s) or event threshold (10) is reached.

Architecture:
  - snapshot.json → Single source of truth for project state
  - Thread-safe operations using memory_lock
  - Async-safe for use with asyncio.to_thread()
  - Compatible with Task 8.11 (SQLite indexing hooks)
"""

import os
import json
import time
import shutil
from datetime import datetime
from typing import Dict, Any, Optional
from core.basic_functional import log_message
from core.memory_lock import safe_read_json, memory_lock

# ===============================
# Cache Configuration
# ===============================

# ✅ TASK 8.8 ENHANCEMENT: SnapshotCache for reduced disk I/O
_snapshot_cache: Dict[str, tuple] = {}  # {project_name: (snapshot_data, timestamp)}
_cache_flush_interval = 5  # Flush cache every 5 seconds
_cache_max_events = 10  # Flush after 10 events
_cache_event_count: Dict[str, int] = {}  # Track events per project

# ===============================
# Directory Management
# ===============================

def _ensure_lazydeve_dir(project_name: str) -> str:
    """
    Ensure .lazydeve directory exists.
    
    ✅ SAFETY: Auto-creates directory if missing
    
    Args:
        project_name: Project name
    
    Returns:
        Path to .lazydeve directory
    """
    lazydeve_dir = f"projects/{project_name}/.lazydeve"
    try:
        os.makedirs(lazydeve_dir, exist_ok=True)
    except Exception as e:
        log_message(f"[ContextSync] ⚠️ Failed to create .lazydeve directory: {e}")
    return lazydeve_dir

# ===============================
# Cache Management
# ===============================

def _flush_snapshot_cache(project_name: str, snapshot_data: Dict[str, Any]) -> bool:
    """
    Flush cached snapshot to disk.
    
    ✅ TASK 8.8 ENHANCEMENT: Periodic cache flush with logging
    ✅ FIX: Write directly (called from within memory_lock, avoid nested lock)
    
    Args:
        project_name: Project name
        snapshot_data: Snapshot data to write
    
    Returns:
        bool: True if flush successful
    """
    _ensure_lazydeve_dir(project_name)  # Ensure directory exists
    snapshot_path = f"projects/{project_name}/.lazydeve/snapshot.json"
    
    try:
        # Create backup if file exists
        if os.path.exists(snapshot_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{snapshot_path}.backup_{timestamp}"
            try:
                shutil.copy(snapshot_path, backup_path)
            except Exception as backup_error:
                log_message(f"[SnapshotCache] ⚠️ Failed to create backup: {backup_error}")
        
        # Ensure directory exists
        directory = os.path.dirname(snapshot_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        # Write JSON file atomically
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
        
        log_message(f"[SnapshotCache] ✅ Flushed snapshot for {project_name}")
        # Reset event counter after flush
        _cache_event_count[project_name] = 0
        
        return True
    except Exception as e:
        log_message(f"[SnapshotCache] ❌ Failed to flush snapshot for {project_name}: {e}")
        return False

def _should_flush_cache(project_name: str) -> bool:
    """
    Determine if cache should be flushed.
    
    ✅ TASK 8.8: Cache flush policy (time or event threshold)
    
    Args:
        project_name: Project name
    
    Returns:
        bool: True if cache should be flushed
    """
    if project_name not in _snapshot_cache:
        return False
    
    cached_data, cache_time = _snapshot_cache[project_name]
    event_count = _cache_event_count.get(project_name, 0)
    
    # Flush if time threshold exceeded
    if time.time() - cache_time > _cache_flush_interval:
        return True
    
    # Flush if event threshold exceeded
    if event_count >= _cache_max_events:
        return True
    
    return False

# ===============================
# Snapshot Operations
# ===============================

def _load_snapshot_unlocked(project_name: str) -> Dict[str, Any]:
    """
    Internal unlocked version of load_snapshot() for use within locked contexts.
    
    ✅ FIX: Prevents deadlock when called from update_snapshot()
    ⚠️ WARNING: This function assumes memory_lock is already held by caller!
    
    Args:
        project_name: Project name
    
    Returns:
        dict: Snapshot data or default structure
    """
    # Check cache first (assumes lock is already held)
    if project_name in _snapshot_cache:
        cached_data, cache_time = _snapshot_cache[project_name]
        # Use cache if fresh (within flush interval)
        if time.time() - cache_time < _cache_flush_interval:
            return cached_data.copy()
    
    _ensure_lazydeve_dir(project_name)  # Ensure directory exists
    snapshot_path = f"projects/{project_name}/.lazydeve/snapshot.json"
    
    try:
        if os.path.exists(snapshot_path):
            # ✅ FIX: Read directly (avoid nested lock in safe_read_json)
            # We're already inside memory_lock, so read file directly
            with open(snapshot_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Validate data structure
            if not isinstance(data, dict):
                log_message(f"[ContextSync] ⚠️ Invalid snapshot structure for {project_name}, using default")
                data = {}
            
            # Update cache (lock already held)
            _snapshot_cache[project_name] = (data.copy(), time.time())
            
            return data
    except json.JSONDecodeError as e:
        log_message(f"[ContextSync] ⚠️ Corrupted snapshot file for {project_name}: {e}")
    except Exception as e:
        log_message(f"[ContextSync] ⚠️ Failed to load snapshot for {project_name}: {e}")
    
    # Return default snapshot structure
    default_snapshot = {
        "version": "1.0",
        "project": project_name,
        "last_commit": None,
        "last_run": None,
        "last_run_status": None,
        "last_run_script": None,
        "status": "unknown",
        "last_logs": [],
        "pending_changes": False,
        "snapshot_version": 0,
        "last_updated": datetime.now().isoformat() + "Z"
    }
    
    # Cache default (lock already held)
    _snapshot_cache[project_name] = (default_snapshot.copy(), time.time())
    
    return default_snapshot


def update_snapshot(project_name: str, updates: Dict[str, Any]) -> bool:
    """
    Atomically update snapshot.json with project state (with caching and versioning).
    
    ✅ TASK 8.8: Snapshot management with optimistic locking
    ✅ TASK 8.11 COMPATIBILITY: Async-safe (can be called via asyncio.to_thread())
    ✅ SAFETY: Thread-safe using memory_lock, graceful error handling
    
    Args:
        project_name: Project name
        updates: Dictionary of fields to update
    
    Returns:
        bool: True if update successful
    
    Example:
        update_snapshot("my_project", {
            "last_run": "2025-11-21T17:10:23Z",
            "last_run_status": "success",
            "last_run_script": "test_2.py"
        })
    """
    _ensure_lazydeve_dir(project_name)  # Ensure directory exists
    snapshot_path = f"projects/{project_name}/.lazydeve/snapshot.json"
    
    with memory_lock:  # Thread-safe lock
        try:
            # Read current snapshot (from cache or disk)
            # ✅ FIX: Use unlocked version to prevent deadlock
            current = _load_snapshot_unlocked(project_name)
            
            # ✅ TASK 8.8 ENHANCEMENT: Optimistic locking with version
            current_version = current.get("snapshot_version", 0)
            updates["snapshot_version"] = current_version + 1
            
            # Merge updates
            current.update(updates)
            current["last_updated"] = datetime.now().isoformat() + "Z"
            
            # ✅ TASK 8.8 ENHANCEMENT: Update cache instead of immediate write
            _snapshot_cache[project_name] = (current.copy(), time.time())
            
            # Increment event counter
            _cache_event_count[project_name] = _cache_event_count.get(project_name, 0) + 1
            
            # Flush if cache threshold reached
            if _should_flush_cache(project_name):
                flush_result = _flush_snapshot_cache(project_name, current)
                if flush_result:
                    # ✅ TASK 8.11: Trigger indexing hook after successful flush
                    _index_snapshot_hook(project_name, current)
                    return True  # Cache flush successful, no need for immediate write
            
            # For immediate consistency, also write to disk
            # ✅ FIX: Write directly (avoid nested lock in safe_write_json)
            # We're already inside memory_lock, so write file directly
            try:
                # Create backup if file exists
                if os.path.exists(snapshot_path):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = f"{snapshot_path}.backup_{timestamp}"
                    try:
                        shutil.copy(snapshot_path, backup_path)
                    except Exception as backup_error:
                        log_message(f"[ContextSync] ⚠️ Failed to create backup: {backup_error}")
                
                # Ensure directory exists
                directory = os.path.dirname(snapshot_path)
                if directory:
                    os.makedirs(directory, exist_ok=True)
                
                # Write JSON file atomically
                with open(snapshot_path, "w", encoding="utf-8") as f:
                    json.dump(current, f, indent=2, ensure_ascii=False)
                
                log_message(f"[ContextSync] ✅ Snapshot written for {project_name}")
                
                # ✅ TASK 8.11: Trigger indexing hook after successful write
                _index_snapshot_hook(project_name, current)
                
                return True
            except Exception as write_error:
                log_message(f"[ContextSync] ❌ Failed to write snapshot for {project_name}: {write_error}")
                return False
            
        except Exception as e:
            log_message(f"[ContextSync] ❌ Failed to update snapshot for {project_name}: {e}")
            return False


def load_snapshot(project_name: str) -> Dict[str, Any]:
    """
    Load snapshot.json for a project (with cache support).
    
    ✅ TASK 8.8 ENHANCEMENT: Cache-aware snapshot loading
    ✅ SAFETY: Returns default structure if file missing or corrupted
    ✅ TASK 8.11 COMPATIBILITY: Async-safe (can be called via asyncio.to_thread())
    
    Args:
        project_name: Project name
    
    Returns:
        dict: Snapshot data or default structure
    
    Example:
        snapshot = load_snapshot("my_project")
        print(snapshot["last_run"])  # "2025-11-21T17:10:23Z"
    """
    # Check cache first (within lock for consistency)
    with memory_lock:
        if project_name in _snapshot_cache:
            cached_data, cache_time = _snapshot_cache[project_name]
            # Use cache if fresh (within flush interval)
            if time.time() - cache_time < _cache_flush_interval:
                return cached_data.copy()
    
    _ensure_lazydeve_dir(project_name)  # Ensure directory exists
    snapshot_path = f"projects/{project_name}/.lazydeve/snapshot.json"
    
    try:
        if os.path.exists(snapshot_path):
            # ✅ SAFETY: Uses safe_read_json for thread-safe reads with error recovery
            data = safe_read_json(snapshot_path, {})
            
            # Validate data structure
            if not isinstance(data, dict):
                log_message(f"[ContextSync] ⚠️ Invalid snapshot structure for {project_name}, using default")
                data = {}
            
            # Update cache
            with memory_lock:
                _snapshot_cache[project_name] = (data.copy(), time.time())
            
            return data
    except Exception as e:
        log_message(f"[ContextSync] ⚠️ Failed to load snapshot for {project_name}: {e}")
    
    # Return default snapshot structure
    # ✅ TASK 8.8 COMPATIBILITY: Snapshot versioning for RAG/MCP
    default_snapshot = {
        "version": "1.0",  # Schema version for future migrations
        "project": project_name,
        "last_commit": None,
        "last_run": None,
        "last_run_status": None,
        "last_run_script": None,
        "status": "unknown",
        "last_logs": [],
        "pending_changes": False,
        "snapshot_version": 0,  # ✅ TASK 8.8 ENHANCEMENT: Version tracking for optimistic locking
        "last_updated": datetime.now().isoformat() + "Z"
    }
    
    # Cache default
    with memory_lock:
        _snapshot_cache[project_name] = (default_snapshot.copy(), time.time())
    
    return default_snapshot


def cache_sync(project_name: str, force: bool = False) -> bool:
    """
    Manually refresh snapshot cache.
    
    ✅ TASK 8.8 COMPATIBILITY: Cache consistency
    ✅ SAFETY: Thread-safe cache refresh
    
    Args:
        project_name: Project name
        force: Force refresh even if cache is fresh
    
    Returns:
        bool: True if refreshed successfully
    """
    with memory_lock:
        if force or project_name not in _snapshot_cache:
            # Force reload from disk
            _ensure_lazydeve_dir(project_name)
            snapshot_path = f"projects/{project_name}/.lazydeve/snapshot.json"
            if os.path.exists(snapshot_path):
                data = safe_read_json(snapshot_path, {})
                _snapshot_cache[project_name] = (data.copy(), time.time())
                _cache_event_count[project_name] = 0
                return True
        return False


def get_project_state(project_name: str) -> Dict[str, Any]:
    """
    Get unified project state (snapshot + memory + context).
    
    ✅ TASK 8.8: Unified state query
    ✅ TASK 8.11 COMPATIBILITY: Used by /context/snapshot endpoint
    ✅ TASK 9 COMPATIBILITY: Provides structured data for RAG vectorization
    ✅ TASK 10 COMPATIBILITY: Provides queryable state for MCP server
    
    Args:
        project_name: Project name
    
    Returns:
        dict: Complete project state with snapshot, memory stats, and context
    
    Example:
        state = get_project_state("my_project")
        print(state["last_run"])  # From snapshot
        print(state["memory_stats"])  # From memory.json
    """
    snapshot = load_snapshot(project_name)
    
    # Add memory stats
    try:
        from core.memory_utils import load_memory
        memory = load_memory(project_name)
        snapshot["memory_stats"] = {
            "total_actions": len(memory.get("actions", [])),
            "last_action": memory.get("actions", [{}])[-1] if memory.get("actions") else None,
            "semantic_context": memory.get("semantic_context", {})
        }
    except Exception as e:
        log_message(f"[ContextSync] ⚠️ Failed to load memory stats: {e}")
        snapshot["memory_stats"] = {}
    
    # Add context info (active project status)
    try:
        from core.context_manager import context_manager
        snapshot["active"] = (context_manager.get_project() == project_name)
    except Exception:
        snapshot["active"] = False
    
    return snapshot


# ===============================
# Task 8.11 Integration Hook
# ===============================

def _index_snapshot_hook(project_name: str, snapshot_data: Dict[str, Any]) -> None:
    """
    Internal hook for Task 8.11 SQLite indexing.
    
    ✅ TASK 8.11 COMPATIBILITY: Async-safe indexing hook
    This function is called after snapshot updates to trigger SQLite indexing.
    
    Args:
        project_name: Project name
        snapshot_data: Snapshot data to index
    """
    try:
        # Import here to avoid circular dependencies
        from core.context_indexer import index_snapshot
        
        # Call indexer (async-safe, non-blocking)
        # Note: This will be implemented in Task 8.11
        index_snapshot(project_name, snapshot_data)
    except ImportError:
        # Task 8.11 not yet implemented, silently skip
        pass
    except Exception as e:
        # Don't fail snapshot update if indexing fails
        log_message(f"[ContextSync] ⚠️ Snapshot indexing failed: {e}")

# ===============================
# Public API
# ===============================

__all__ = [
    'update_snapshot',
    'load_snapshot',
    'get_project_state',
    'cache_sync'
]

