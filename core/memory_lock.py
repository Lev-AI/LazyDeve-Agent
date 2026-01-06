"""
memory_lock.py
--------------
Global thread-safe lock for memory and JSON file operations.

This module provides centralized thread-safety for all memory-related operations
across the LazyDeve agent to prevent race conditions and data corruption.

Usage:
    from core.memory_lock import memory_lock, safe_read_json, safe_write_json
    
    # Direct lock usage:
    with memory_lock:
        # Your critical section
        
    # Safe JSON operations:
    data = safe_read_json("path/to/file.json")
    safe_write_json("path/to/file.json", data)
"""

import threading
import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

# ===============================
# Global Thread-Safe Lock
# ===============================

memory_lock = threading.Lock()
"""
Global lock for all memory-related operations.
Use this lock for any operations involving:
- .lazydeve/memory.json
- .lazydeve/config.json  
- .lazydeve/stats.json
- .lazydeve/logs/ directory
- memory.json (root state file)
"""

# ===============================
# Safe JSON Operations
# ===============================

def safe_read_json(path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Thread-safe JSON file reading with automatic error recovery.
    
    Args:
        path: Path to JSON file
        default: Default value to return if file doesn't exist or is corrupted
        
    Returns:
        dict: Parsed JSON data or default value
        
    Features:
        - Thread-safe with global lock
        - Automatic backup of corrupted files
        - Returns default value on errors
        - Handles missing files gracefully
    """
    if default is None:
        default = {}
        
    with memory_lock:
        try:
            if not os.path.exists(path):
                return default.copy()
                
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
                
        except json.JSONDecodeError as e:
            # Backup corrupted file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{path}.corrupted_{timestamp}"
            try:
                shutil.copy(path, backup_path)
                print(f"[MemoryLock] Corrupted JSON backed up to: {backup_path}")
            except Exception as backup_error:
                print(f"[MemoryLock] Failed to backup corrupted file: {backup_error}")
            
            return default.copy()
            
        except Exception as e:
            print(f"[MemoryLock] Error reading {path}: {e}")
            return default.copy()


def safe_write_json(path: str, data: Dict[str, Any], indent: int = 2, 
                    ensure_ascii: bool = False, create_backup: bool = False) -> bool:
    """
    Thread-safe JSON file writing with optional backup.
    
    Args:
        path: Path to JSON file
        data: Dictionary to write
        indent: JSON indentation level (default: 2)
        ensure_ascii: Whether to escape non-ASCII characters (default: False)
        create_backup: Whether to create backup before writing (default: False)
        
    Returns:
        bool: True if write succeeded, False otherwise
        
    Features:
        - Thread-safe with global lock
        - Optional backup before writing
        - Atomic write operation
        - Directory creation if needed
        - Comprehensive error handling
    """
    with memory_lock:
        try:
            # Create backup if requested and file exists
            if create_backup and os.path.exists(path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{path}.backup_{timestamp}"
                try:
                    shutil.copy(path, backup_path)
                except Exception as backup_error:
                    print(f"[MemoryLock] Warning: Failed to create backup: {backup_error}")
            
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            # Write JSON file
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            
            # ✅ TASK 8.10: Self-Trigger FIFO Cleanup - Unified maintenance for ALL .lazydeve JSON files
            # Pattern: Check current file, if exceeds → trigger unified maintenance (check ALL, trim ALL)
            if ".lazydeve" in path and path.endswith(".json") and not path.endswith("config.json"):
                try:
                    from core.file_maintenance import maintain_lazydeve_json_files, MAX_CONTEXT_JSON_SIZE_MB
                    # Check if CURRENT file exceeds limit (same pattern as logs)
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                    if size_mb > MAX_CONTEXT_JSON_SIZE_MB:
                        # Current file exceeds → trigger unified maintenance (check ALL, trim ALL)
                        # Extract project name from path: projects/{project}/.lazydeve/{file}.json
                        path_parts = path.replace("\\", "/").split("/")
                        if "projects" in path_parts and ".lazydeve" in path_parts:
                            project_idx = path_parts.index("projects")
                            if project_idx + 1 < len(path_parts):
                                project_name = path_parts[project_idx + 1]
                                maintain_lazydeve_json_files(project_name, MAX_CONTEXT_JSON_SIZE_MB)
                except Exception as e:
                    # Non-critical, don't fail write operation
                    pass
            
            return True
            
        except Exception as e:
            print(f"[MemoryLock] Error writing {path}: {e}")
            return False


def safe_append_log(path: str, message: str, timestamp: bool = True) -> bool:
    """
    Thread-safe log file appending.
    
    Args:
        path: Path to log file
        message: Message to append
        timestamp: Whether to add timestamp prefix (default: True)
        
    Returns:
        bool: True if append succeeded, False otherwise
        
    Features:
        - Thread-safe with global lock
        - Optional timestamp prefix
        - Directory creation if needed
        - Ensures newline termination
    """
    with memory_lock:
        try:
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            # Format message
            if timestamp:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                formatted_message = f"[{ts}] {message}"
            else:
                formatted_message = message
            
            # Ensure newline
            if not formatted_message.endswith("\n"):
                formatted_message += "\n"
            
            # Append to file
            with open(path, "a", encoding="utf-8") as f:
                f.write(formatted_message)
            
            # ✅ TASK 8.10: Self-Trigger FIFO Cleanup - Check and trim log files after append
            # Only check files in logs/ directory (handle both relative and absolute paths)
            normalized_path = os.path.normpath(path).replace("\\", "/")
            if "/logs/" in normalized_path or normalized_path.startswith("logs/") or normalized_path.endswith(".log"):
                try:
                    from core.file_maintenance import trim_log_file, MAX_LOG_SIZE_MB
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                    if size_mb > MAX_LOG_SIZE_MB:
                        trim_log_file(path, MAX_LOG_SIZE_MB)
                except Exception as e:
                    # Non-critical, don't fail append operation
                    pass
            
            return True
            
        except Exception as e:
            print(f"[MemoryLock] Error appending to {path}: {e}")
            return False


# ===============================
# Context Manager for Custom Operations
# ===============================

class MemoryLockContext:
    """
    Context manager for custom memory operations with automatic lock handling.
    
    Usage:
        with MemoryLockContext() as lock:
            # Your memory operations here
            # Lock is automatically acquired and released
    """
    
    def __enter__(self):
        memory_lock.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        memory_lock.release()
        return False  # Don't suppress exceptions


# ===============================
# Utility Functions
# ===============================

def is_locked() -> bool:
    """
    Check if memory lock is currently held.
    
    Returns:
        bool: True if lock is held, False otherwise
        
    Note:
        This is primarily for debugging/monitoring purposes.
    """
    return memory_lock.locked()


def get_lock_info() -> Dict[str, Any]:
    """
    Get information about the memory lock state.
    
    Returns:
        dict: Lock state information
    """
    return {
        "locked": memory_lock.locked(),
        "lock_type": "threading.Lock",
        "module": "core.memory_lock",
        "purpose": "Global thread-safety for memory operations"
    }


# ===============================
# Module Information
# ===============================

__all__ = [
    'memory_lock',
    'safe_read_json',
    'safe_write_json',
    'safe_append_log',
    'MemoryLockContext',
    'is_locked',
    'get_lock_info'
]

if __name__ == "__main__":
    # Module self-test
    print("Memory Lock Module - Self Test")
    print("=" * 50)
    print(f"Lock state: {get_lock_info()}")
    print(f"Lock available: {not is_locked()}")
    print("=" * 50)
    print("✅ Memory lock module loaded successfully")

