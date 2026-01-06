"""
Unified File Maintenance Layer
✅ TASK 8.10 ENHANCED: FIFO Rotation for Memory, Context JSON, Logs, and Aider History

Maintains:
- Project memory.json (FIFO rotation, preserves stats/context)
- All .json context files in .lazydeve/ (3MB per file)
- Log files in logs/ directory (3MB per file)
- .aider.chat.history.md in root (3MB limit)
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from core.basic_functional import log_message
from core.memory_lock import safe_read_json, safe_write_json

# ===============================
# Configuration Constants
# ===============================

# Memory limits (per project)
MAX_MEMORY_ACTIONS = int(os.getenv("LAZYDEVE_MEMORY_MAX_ENTRIES", 300))
# ✅ TEST MODE: Temporarily set to 200 KB (0.2 MB) for testing - change back to 5 after testing
MAX_MEMORY_SIZE_MB = float(os.getenv("LAZYDEVE_MEMORY_LIMIT_MB", 0.2))  # 200 KB for testing

# Context JSON file limits (per file in .lazydeve/)
# ✅ TEST MODE: Temporarily set to 200 KB (0.2 MB) for testing - change back to 3.0 after testing
MAX_CONTEXT_JSON_SIZE_MB = float(os.getenv("LAZYDEVE_CONTEXT_JSON_LIMIT_MB", 0.2))  # 200 KB for testing

# Log file limits
# ✅ TEST MODE: Temporarily set to 200 KB (0.2 MB) for testing - change back to 3.0 after testing
MAX_LOG_SIZE_MB = float(os.getenv("LAZYDEVE_LOG_LIMIT_MB", 0.2))  # 200 KB for testing
LOGS_DIRECTORY = "logs"

# Aider history limit
# ✅ TEST MODE: Temporarily set to 200 KB (0.2 MB) for testing - change back to 3.0 after testing
MAX_AIDER_HISTORY_SIZE_MB = float(os.getenv("LAZYDEVE_AIDER_LIMIT_MB", 0.2))  # 200 KB for testing
AIDER_HISTORY_FILE = ".aider.chat.history.md"


# ===============================
# Memory Maintenance
# ===============================

def get_project_memory_limits(project_name: str) -> Tuple[int, int]:
    """
    Get memory limits for a project (config.json > env > defaults).
    ✅ TASK 8.10 COMPATIBILITY: Per-project memory limit overrides
    
    Args:
        project_name: Project name
    
    Returns:
        tuple: (max_entries, max_size_mb)
    """
    config_path = f"projects/{project_name}/.lazydeve/config.json"
    if os.path.exists(config_path):
        try:
            config = safe_read_json(config_path, {})
            memory_config = config.get("memory", {})
            max_entries = memory_config.get("max_entries", MAX_MEMORY_ACTIONS)
            max_size_mb = memory_config.get("max_size_mb", MAX_MEMORY_SIZE_MB)
            return (max_entries, max_size_mb)
        except Exception:
            pass
    
    return (MAX_MEMORY_ACTIONS, MAX_MEMORY_SIZE_MB)


def fifo_trim_memory(project_name: str, max_entries: int = None, max_size_mb: int = None) -> bool:
    """
    FIFO-based cleanup for memory.json with version check.
    ✅ TASK 8.10 COMPATIBILITY: Version-aware cleanup with configurable limits
    ✅ TASK 8.11 & 9 COMPATIBILITY: Preserves stats and semantic_context
    
    Keeps most recent entries and trims excessive data.
    Preserves stats and semantic_context (not trimmed).
    
    Args:
        project_name: Project name
        max_entries: Maximum number of actions (None = use config)
        max_size_mb: Maximum file size in MB (None = use config)
    
    Returns:
        bool: True if trimmed, False otherwise
    """
    if max_entries is None or max_size_mb is None:
        config_entries, config_size = get_project_memory_limits(project_name)
        max_entries = max_entries or config_entries
        max_size_mb = max_size_mb or config_size
    
    try:
        memory_path = f"projects/{project_name}/.lazydeve/memory.json"
        if not os.path.exists(memory_path):
            return False
        
        data = safe_read_json(memory_path, {})
        
        # Ensure version field exists
        if "version" not in data:
            data["version"] = "1.0"
            log_message(f"[FileMaintenance] Added version field to memory.json for {project_name}")
        
        version = data.get("version", "1.0")
        if version != "1.0":
            log_message(f"[FileMaintenance] ⚠️ Unsupported memory version: {version} (expected 1.0)")
        
        actions = data.get("actions", [])
        before_count = len(actions)
        
        # Trim by count (FIFO - keep most recent)
        if len(actions) > max_entries:
            actions = actions[-max_entries:]
            log_message(f"[FileMaintenance] Trimmed actions by count: {before_count} → {len(actions)}")
        
        # Trim by file size (FIFO - keep most recent)
        size_mb = os.path.getsize(memory_path) / (1024 * 1024)
        if size_mb > max_size_mb:
            # ✅ TASK 8.10: Trim to 50% of max_size_mb (100KB from 200KB)
            target_size_mb = max_size_mb * 0.5
            target_size_bytes = int(target_size_mb * 1024 * 1024)
            
            # Keep trimming oldest actions until file size <= target
            trimmed = False
            while len(actions) > 1:
                # Calculate current size with remaining actions
                data["actions"] = actions
                test_size_bytes = len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                
                if test_size_bytes <= target_size_bytes:
                    break  # Size is acceptable
                
                # Remove oldest action (FIFO)
                actions.pop(0)
                trimmed = True
            
            if trimmed:
                log_message(f"[FileMaintenance] Trimmed actions by size: {before_count} → {len(actions)} (target: {target_size_mb:.2f}MB)")
        
        # ✅ TASK 8.11 & 9 COMPATIBILITY: Preserve stats and semantic_context
        data["actions"] = actions
        data["last_cleanup"] = datetime.now().isoformat() + "Z"
        
        # ✅ TASK 8.10: No backup needed - simple FIFO trim
        safe_write_json(memory_path, data, create_backup=False)
        after_count = len(actions)
        
        if before_count != after_count:
            log_message(f"[FileMaintenance] ✅ Memory trimmed: {before_count} → {after_count} actions")
        
        return True
    
    except Exception as e:
        log_message(f"[FileMaintenance] ❌ Memory cleanup failed: {e}")
        return False


def reset_memory(project_name: str, preserve_stats: bool = True) -> bool:
    """
    Soft reset memory.json (optional API hook).
    ✅ TASK 8.10 COMPATIBILITY: Preserves stats and semantic_context
    
    Args:
        project_name: Project name
        preserve_stats: If True, preserves stats and semantic_context
    
    Returns:
        bool: True if reset successful, False otherwise
    """
    try:
        memory_path = f"projects/{project_name}/.lazydeve/memory.json"
        if not os.path.exists(memory_path):
            return False

        data = safe_read_json(memory_path, {})
        stats = data.get("stats") if preserve_stats else {}
        semantic_context = data.get("semantic_context", {}) if preserve_stats else {}

        new_data = {
            "version": "1.0",
            "project": project_name,
            "actions": [],
            "stats": stats,
            "semantic_context": semantic_context,  # ✅ Preserve semantic context
            "last_reset": datetime.now().isoformat() + "Z"
        }

        safe_write_json(memory_path, new_data, create_backup=True)
        log_message(f"[FileMaintenance] 🔄 Memory reset for project: {project_name}")
        return True

    except Exception as e:
        log_message(f"[FileMaintenance] ❌ Reset failed: {e}")
        return False


# ===============================
# Context JSON Files Maintenance
# ===============================

def trim_json_file_fifo(file_path: str, max_size_mb: float = MAX_CONTEXT_JSON_SIZE_MB) -> bool:
    """
    Trim JSON file to max_size_mb using FIFO (keep most recent entries).
    ✅ TASK 8.10 ENHANCED: Context JSON file maintenance
    
    Handles different JSON structures:
    - Arrays: Keep most recent N items
    - Objects with arrays: Trim array fields, preserve structure
    - Objects with nested data: Trim based on size, preserve keys
    
    Args:
        file_path: Path to JSON file
        max_size_mb: Maximum file size in MB (default: 3MB)
    
    Returns:
        bool: True if trimmed, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if size_mb <= max_size_mb:
            return False  # No trimming needed
        
        # Read JSON file
        data = safe_read_json(file_path, {})
        
        if not data:
            return False
        
        # ✅ TASK 8.10: Calculate target size (trim to 50% of max - provides larger buffer)
        target_size_bytes = int(max_size_mb * 1024 * 1024 * 0.5)
        
        # Strategy: Identify array fields and trim them (FIFO)
        trimmed = False
        
        # Case 1: Root is an array (e.g., events array)
        if isinstance(data, list):
            original_count = len(data)
            # Keep most recent items
            while len(json.dumps(data, ensure_ascii=False).encode('utf-8')) > target_size_bytes and len(data) > 1:
                data.pop(0)  # Remove oldest (FIFO)
                trimmed = True
            
            if trimmed:
                # ✅ TASK 8.10: No backup needed - simple FIFO trim
                safe_write_json(file_path, data, create_backup=False)
                new_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                log_message(f"[FileMaintenance] ✅ JSON array trimmed: {file_path} ({size_mb:.2f}MB → {new_size_mb:.2f}MB, {original_count} → {len(data)} items)")
                return True
        
        # Case 2: Object with array fields (e.g., {"events": [...], "snapshots": [...]})
        elif isinstance(data, dict):
            # Find array fields that can be trimmed
            array_fields = []
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    array_fields.append(key)
            
            if array_fields:
                # Trim each array field (FIFO - keep most recent)
                for field in array_fields:
                    original_count = len(data[field])
                    while len(json.dumps(data, ensure_ascii=False).encode('utf-8')) > target_size_bytes and len(data[field]) > 1:
                        data[field].pop(0)  # Remove oldest (FIFO)
                        trimmed = True
                    
                    if len(data[field]) < original_count:
                        log_message(f"[FileMaintenance] Trimmed {field}: {original_count} → {len(data[field])} items")
                
                # ✅ TASK 8.10.1: Special handling for commit_history.json
                # Ensure last_commit stays in sync with history[0] after trimming
                if os.path.basename(file_path) == "commit_history.json" and "history" in data and data["history"]:
                    if data.get("last_commit") and data["history"][0].get("commit_id") != data["last_commit"].get("commit_id"):
                        # Sync last_commit with most recent in history
                        data["last_commit"] = data["history"][0]
                        log_message(f"[FileMaintenance] Synced last_commit with history[0] after trim")
                
                if trimmed:
                    # ✅ TASK 8.10: No backup needed - simple FIFO trim
                    safe_write_json(file_path, data, create_backup=False)
                    new_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    log_message(f"[FileMaintenance] ✅ JSON object trimmed: {file_path} ({size_mb:.2f}MB → {new_size_mb:.2f}MB)")
                    return True
        
        # Case 3: Object without arrays - preserve structure, log warning
        if size_mb > max_size_mb:
            log_message(f"[FileMaintenance] ⚠️ JSON file {file_path} exceeds limit but has no array fields to trim (preserving structure)")
        
        return False
    
    except Exception as e:
        log_message(f"[FileMaintenance] ❌ JSON trim failed for {file_path}: {e}")
        return False


def maintain_lazydeve_json_files(project_name: str, max_size_mb: float = MAX_CONTEXT_JSON_SIZE_MB) -> int:
    """
    Unified maintenance: Treat ALL .lazydeve JSON files (including memory.json) as ONE UNIT.
    If ANY file exceeds limit, trim ALL files by 50%.
    ✅ TASK 8.10 ENHANCED: Unified maintenance for all context JSON files
    
    Includes:
    - memory.json (now included in unified maintenance)
    - snapshot.json
    - session_context.json
    - commit_history.json (✅ TASK 8.10.1: Unified commit history)
    - context_full.json (✅ TASK 8.10.1.1 PHASE 6: Unified context structure)
    - Any other .json files in .lazydeve/
    
    Note: commit_report.json is deprecated (merged into commit_history.json)
    
    Excludes:
    - config.json (configuration, should not be trimmed)
    
    Logic:
    - Check ALL .json files (including memory.json)
    - If ANY file exceeds max_size_mb, trim ALL files by 50%
    - This ensures consistent maintenance across all context files
    
    Args:
        project_name: Project name
        max_size_mb: Maximum size per JSON file in MB (if any exceeds, all are trimmed)
    
    Returns:
        int: Number of files trimmed
    """
    lazydeve_dir = f"projects/{project_name}/.lazydeve"
    
    if not os.path.exists(lazydeve_dir):
        return 0
    
    trimmed_count = 0
    
    try:
        # Get all .json files (INCLUDING memory.json, excluding config.json)
        json_files = []
        for file in os.listdir(lazydeve_dir):
            if file.endswith('.json'):
                file_path = os.path.join(lazydeve_dir, file)
                if os.path.isfile(file_path):
                    # Exclude only config.json (memory.json is now included)
                    if file != 'config.json':
                        json_files.append(file_path)
        
        if not json_files:
            return 0
        
        # ✅ UNIFIED LOGIC: Check if ANY file exceeds limit
        any_file_exceeds = False
        for json_file in json_files:
            size_mb = os.path.getsize(json_file) / (1024 * 1024)
            if size_mb > max_size_mb:
                any_file_exceeds = True
                log_message(f"[FileMaintenance] ⚠️ File exceeds limit: {os.path.basename(json_file)} ({size_mb:.2f}MB > {max_size_mb:.2f}MB)")
                break
        
        # ✅ UNIFIED LOGIC: If ANY file exceeds, trim ALL files by 50%
        if any_file_exceeds:
            log_message(f"[FileMaintenance] 🔄 Unified trim triggered: Any file exceeded {max_size_mb:.2f}MB, trimming ALL {len(json_files)} file(s) by 50%")
            
            for json_file in json_files:
                # ✅ TASK 8.11: Track row counts before trim for sync_metadata
                file_name = os.path.basename(json_file)
                row_count_before = 0
                
                # Count rows in SQLite before trim (if context_full.json)
                if file_name == "context_full.json":
                    try:
                        from core.context_indexer import _get_connection
                        conn = _get_connection(project_name)
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM commits WHERE project = ?", (project_name,))
                        row_count_before = cursor.fetchone()[0]
                        conn.close()
                    except Exception:
                        pass
                
                # Use appropriate trim function based on file type
                if json_file.endswith('memory.json'):
                    # Use memory-specific trim (preserves stats/semantic_context)
                    if fifo_trim_memory(project_name, max_size_mb=max_size_mb):
                        trimmed_count += 1
                else:
                    # Use generic JSON trim
                    if trim_json_file_fifo(json_file, max_size_mb):
                        trimmed_count += 1
                        
                        # ✅ TASK 8.11: Update sync_metadata after trimming context_full.json
                        if file_name == "context_full.json":
                            try:
                                from core.context_indexer import update_sync_metadata_on_trim, _get_connection
                                # Count rows after trim
                                row_count_after = 0
                                try:
                                    conn = _get_connection(project_name)
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT COUNT(*) FROM commits WHERE project = ?", (project_name,))
                                    row_count_after = cursor.fetchone()[0]
                                    conn.close()
                                except Exception:
                                    pass
                                
                                # Update sync_metadata
                                update_sync_metadata_on_trim(project_name, file_name, row_count_before, row_count_after)
                                log_message(f"[FileMaintenance] ✅ Updated sync_metadata for {file_name} trim (rows: {row_count_before} → {row_count_after})")
                            except Exception as e:
                                log_message(f"[FileMaintenance] ⚠️ Failed to update sync_metadata: {e}")
            
            if trimmed_count > 0:
                log_message(f"[FileMaintenance] ✅ Unified maintenance: Trimmed {trimmed_count}/{len(json_files)} file(s) in {lazydeve_dir}")
        
        return trimmed_count
    
    except Exception as e:
        log_message(f"[FileMaintenance] ❌ Unified maintenance failed for {project_name}: {e}")
        return 0


# ===============================
# Log File Maintenance
# ===============================

def trim_log_file(file_path: str, max_size_mb: float = MAX_LOG_SIZE_MB) -> bool:
    """
    Trim log file to max_size_mb using FIFO (keep most recent lines).
    ✅ TASK 8.10 ENHANCED: Log file maintenance
    
    Args:
        file_path: Path to log file
        max_size_mb: Maximum file size in MB (default: 3MB)
    
    Returns:
        bool: True if trimmed, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if size_mb <= max_size_mb:
            return False  # No trimming needed
        
        # Read all lines
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if not lines:
            return False
        
        # ✅ TASK 8.10: Calculate target size (trim to 50% of max - provides larger buffer)
        target_size_bytes = int(max_size_mb * 1024 * 1024 * 0.5)
        
        # Keep most recent lines (FIFO - oldest first, so keep last N lines)
        trimmed_lines = []
        current_size = 0
        
        # Start from end (most recent) and work backwards
        for line in reversed(lines):
            line_size = len(line.encode('utf-8'))
            if current_size + line_size > target_size_bytes:
                break
            trimmed_lines.insert(0, line)  # Insert at beginning to maintain order
            current_size += line_size
        
        # ✅ TASK 8.10: No backup needed - simple FIFO trim
        # Write trimmed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(trimmed_lines)
        
        new_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        log_message(f"[FileMaintenance] ✅ Log trimmed: {file_path} ({size_mb:.2f}MB → {new_size_mb:.2f}MB)")
        return True
    
    except Exception as e:
        log_message(f"[FileMaintenance] ❌ Log trim failed for {file_path}: {e}")
        return False


def maintain_logs_directory(logs_dir: str = LOGS_DIRECTORY, max_size_mb: float = MAX_LOG_SIZE_MB) -> int:
    """
    Maintain all log files in logs directory.
    ✅ TASK 8.10 ENHANCED: Automatic log file maintenance
    
    Args:
        logs_dir: Directory containing log files
        max_size_mb: Maximum size per log file in MB
    
    Returns:
        int: Number of files trimmed
    """
    if not os.path.exists(logs_dir):
        return 0
    
    trimmed_count = 0
    
    try:
        # Get all .log and .json files in logs directory
        log_files = []
        for file in os.listdir(logs_dir):
            file_path = os.path.join(logs_dir, file)
            if os.path.isfile(file_path) and (file.endswith('.log') or file.endswith('.json')):
                log_files.append(file_path)
        
        # Trim each log file
        for log_file in log_files:
            if trim_log_file(log_file, max_size_mb):
                trimmed_count += 1
        
        if trimmed_count > 0:
            log_message(f"[FileMaintenance] ✅ Maintained {trimmed_count} log file(s) in {logs_dir}")
        
        return trimmed_count
    
    except Exception as e:
        log_message(f"[FileMaintenance] ❌ Log directory maintenance failed: {e}")
        return 0


# ===============================
# Aider History Maintenance
# ===============================

def trim_aider_history(file_path: str = AIDER_HISTORY_FILE, max_size_mb: float = MAX_AIDER_HISTORY_SIZE_MB) -> bool:
    """
    Trim .aider.chat.history.md to max_size_mb using FIFO (keep most recent entries).
    ✅ TASK 8.10 ENHANCED: Aider history maintenance
    
    Args:
        file_path: Path to .aider.chat.history.md (default: root directory)
        max_size_mb: Maximum file size in MB (default: 3MB)
    
    Returns:
        bool: True if trimmed, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if size_mb <= max_size_mb:
            return False  # No trimming needed
        
        # Read all lines
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if not lines:
            return False
        
        # ✅ TASK 8.10: Calculate target size (trim to 50% of max - provides larger buffer)
        target_size_bytes = int(max_size_mb * 1024 * 1024 * 0.5)
        
        # Aider history is markdown, try to preserve structure
        # Look for markdown headers or separators to trim at logical boundaries
        trimmed_lines = []
        current_size = 0
        
        # Keep most recent lines (FIFO)
        for line in reversed(lines):
            line_size = len(line.encode('utf-8'))
            if current_size + line_size > target_size_bytes:
                break
            trimmed_lines.insert(0, line)
            current_size += line_size
        
        # ✅ TASK 8.10: No backup needed - simple FIFO trim
        # Write trimmed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(trimmed_lines)
        
        new_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        log_message(f"[FileMaintenance] ✅ Aider history trimmed: {file_path} ({size_mb:.2f}MB → {new_size_mb:.2f}MB)")
        return True
    
    except Exception as e:
        log_message(f"[FileMaintenance] ❌ Aider history trim failed for {file_path}: {e}")
        return False


# ===============================
# Unified Maintenance Functions
# ===============================

def maintain_all_files(project_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Unified maintenance function for all file types.
    ✅ TASK 8.10 ENHANCED: Single entry point for all maintenance
    
    Args:
        project_name: Optional project name (for memory and context JSON maintenance)
    
    Returns:
        dict: Maintenance results
    """
    results = {
        "memory_trimmed": False,
        "context_json_trimmed": 0,
        "logs_trimmed": 0,
        "aider_trimmed": False
    }
    
    # Memory maintenance (if project specified)
    if project_name:
        results["memory_trimmed"] = fifo_trim_memory(project_name)
        # Context JSON files maintenance
        results["context_json_trimmed"] = maintain_lazydeve_json_files(project_name, MAX_CONTEXT_JSON_SIZE_MB)
    
    # Log files maintenance
    results["logs_trimmed"] = maintain_logs_directory(LOGS_DIRECTORY, MAX_LOG_SIZE_MB)
    
    # Aider history maintenance
    results["aider_trimmed"] = trim_aider_history(AIDER_HISTORY_FILE, MAX_AIDER_HISTORY_SIZE_MB)
    
    return results


# ===============================
# Self-Trigger FIFO Cleanup (No Event Bus)
# ===============================
# ✅ TASK 8.10: Self-Trigger approach - files monitor themselves
# Maintenance is triggered automatically after each write operation
# No event bus or background jobs needed

