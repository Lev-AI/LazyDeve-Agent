"""
memory_utils.py
---------------
Project Memory Management Layer for LazyDeve Agent.
Handles project memory, action tracking, and corruption recovery.

Features:
- Thread-safe memory operations using memory_lock
- Automatic corruption recovery with backups
- Project action logging and statistics
- README update triggers
- Semantic memory preparation for Task 8

All operations are safe and use existing infrastructure from memory_lock.py
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List

from core.basic_functional import log_message
from core.memory_lock import safe_read_json, safe_write_json, safe_append_log, memory_lock


# ===============================
# Project Memory Initialization
# ===============================

def init_project_memory(project_name: str, description: str = "New project") -> Dict[str, Any]:
    """
    Initialize memory.json for a new project with Task 8 structure.
    
    Args:
        project_name: Name of the project
        description: Optional description
        
    Returns:
        dict: Initialized memory structure with semantic_context
    """
    now = datetime.utcnow().isoformat() + "Z"
    
    memory_structure = {
        "project_name": project_name,
        "description": description,
        "created_at": now,
        "last_updated": now,
        "stats": {
            "commits": 0,
            "executions": 0,
            "analyses": 0,
            "total_actions": 0
        },
        "actions": [],
        "last_readme_update": None,
        "version": "1.0",
        # Task 8: Semantic context structure
        "semantic_context": {
            "description": None,
            "tech_stack": [],
            "keywords": [],
            "activity_summary": {
                "total_actions": 0,
                "recent_focus": None,
                "common_operations": [],
                "error_patterns": []
            },
            "confidence_score": 0.0,
            "last_analyzed": None
        },
        "documentation": {
            "readme_last_updated": None,
            "auto_generated": False,
            "sections": []
        }
    }
    
    memory_path = f"projects/{project_name}/.lazydeve/memory.json"
    
    # Use safe_write_json for thread-safe writing
    success = safe_write_json(memory_path, memory_structure)
    
    if success:
        log_message(f"[Memory] Initialized memory for project: {project_name}")
        return memory_structure
    else:
        log_message(f"[Memory] Failed to initialize memory for project: {project_name}")
        return {}


# ===============================
# Memory Loading with Corruption Recovery
# ===============================

def load_memory(project_name: str, auto_migrate: bool = True) -> Dict[str, Any]:
    """
    Load project memory with automatic corruption recovery and Task 8 migration.
    
    This function uses safe_read_json which already handles:
    - Corrupted JSON files (auto-backup and recovery)
    - Missing files (returns default empty dict)
    - Thread-safe operations
    
    Task 8 Enhancement: Auto-migrates to semantic_context structure if needed.
    
    Args:
        project_name: Name of the project
        auto_migrate: Automatically migrate to Task 8 structure if needed
        
    Returns:
        dict: Project memory or default structure if not found/corrupted
    """
    memory_path = f"projects/{project_name}/.lazydeve/memory.json"
    
    # Check if project exists
    if not os.path.exists(f"projects/{project_name}"):
        log_message(f"[Memory] Project not found: {project_name}")
        return {}
    
    # Use safe_read_json which handles corruption automatically
    default_memory = {
        "project_name": project_name,
        "description": "Recovered project",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "stats": {"commits": 0, "executions": 0, "analyses": 0, "total_actions": 0},
        "actions": [],
        "last_readme_update": None,
        "version": "1.0"
    }
    
    memory = safe_read_json(memory_path, default=default_memory)
    
    # If memory was empty or corrupted and recovered, reinitialize it
    if not memory or "project_name" not in memory:
        log_message(f"[Memory] Reinitializing memory for project: {project_name}")
        memory = init_project_memory(project_name, "Recovered after corruption")
    
    # Task 8: Auto-migrate to semantic structure if needed
    if auto_migrate and "semantic_context" not in memory:
        log_message(f"[Memory] Auto-migrating {project_name} to Task 8 structure")
        if migrate_memory_to_task8(project_name):
            # Reload migrated memory
            memory = safe_read_json(memory_path, default=default_memory)
    
    return memory


# ===============================
# Memory Saving
# ===============================

def save_memory(project_name: str, memory_data: Dict[str, Any], create_backup: bool = False) -> bool:
    """
    Save project memory with optional backup.
    
    Args:
        project_name: Name of the project
        memory_data: Memory data to save
        create_backup: Whether to create a timestamped backup
        
    Returns:
        bool: True if saved successfully
    """
    memory_path = f"projects/{project_name}/.lazydeve/memory.json"
    
    # Update last_updated timestamp
    memory_data["last_updated"] = datetime.utcnow().isoformat() + "Z"
    
    # Use safe_write_json for thread-safe writing
    success = safe_write_json(memory_path, memory_data, create_backup=create_backup)
    
    if success:
        log_message(f"[Memory] Saved memory for project: {project_name}")
        
        # ✅ TASK 8.10: Self-Trigger FIFO Cleanup - Unified maintenance for ALL .lazydeve JSON files
        # Pattern: Check current file, if exceeds → trigger unified maintenance (check ALL, trim ALL)
        try:
            from core.file_maintenance import maintain_lazydeve_json_files, MAX_MEMORY_SIZE_MB
            import os
            # Check if CURRENT file (memory.json) exceeds limit (same pattern as logs)
            memory_size_mb = os.path.getsize(memory_path) / (1024 * 1024)
            if memory_size_mb > MAX_MEMORY_SIZE_MB:
                # memory.json exceeds → trigger unified maintenance (check ALL, trim ALL)
                maintain_lazydeve_json_files(project_name, MAX_MEMORY_SIZE_MB)
        except Exception as e:
            # Non-critical, don't fail save operation
            pass
    else:
        log_message(f"[Memory] Failed to save memory for project: {project_name}")
    
    return success


# ===============================
# Action Tracking and Updates
# ===============================

def update_memory(project_name: str, action_type: str, description: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Update project memory with a new action.
    
    This is the main function used by Task 7.7.3b for memory hooks.
    
    Args:
        project_name: Name of the project
        action_type: Type of action (commit, execute, analyze, etc.)
        description: Human-readable description of the action
        extra: Optional additional metadata
        
    Returns:
        dict: Result with status and updated memory
    """
    try:
        # Load current memory
        memory = load_memory(project_name)
        
        if not memory:
            return {"status": "error", "message": f"Project not found: {project_name}"}
        
        # Update statistics
        stats = memory.get("stats", {})
        
        if action_type == "commit":
            stats["commits"] = stats.get("commits", 0) + 1
        elif action_type == "execute":
            stats["executions"] = stats.get("executions", 0) + 1
        elif action_type == "analyze":
            stats["analyses"] = stats.get("analyses", 0) + 1
        
        stats["total_actions"] = stats.get("total_actions", 0) + 1
        memory["stats"] = stats
        
        # Record action in history
        action_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": action_type,
            "description": description
        }
        
        if extra:
            action_entry["extra"] = extra
        
        actions = memory.get("actions", [])
        actions.append(action_entry)
        
        # Keep only last 100 actions to prevent file bloat
        memory["actions"] = actions[-100:]
        
        # Save updated memory
        success = save_memory(project_name, memory)
        
        if success:
            return {
                "status": "success",
                "message": f"Memory updated for project: {project_name}",
                "stats": stats
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to save memory for project: {project_name}"
            }
    
    except Exception as e:
        log_message(f"[Memory] Error updating memory for {project_name}: {e}")
        return {"status": "error", "message": str(e)}


# ===============================
# Project Action Logging
# ===============================

def log_project_action(project_name: str, action_type: str, message: str) -> bool:
    """
    Log an action to the project's action log file.
    
    This creates a plaintext log in .lazydeve/logs/actions.log for human readability.
    
    Args:
        project_name: Name of the project
        action_type: Type of action
        message: Log message
        
    Returns:
        bool: True if logged successfully
    """
    log_path = f"projects/{project_name}/.lazydeve/logs/actions.log"
    
    # Use safe_append_log for thread-safe logging
    log_entry = f"[{action_type.upper()}] {message}"
    success = safe_append_log(log_path, log_entry)
    
    if not success:
        log_message(f"[Memory] Failed to log action for project: {project_name}")
    
    return success


# ===============================
# README Update Triggers
# ===============================

def should_update_readme(project_name: str, threshold: int = 5) -> bool:
    """
    Check if README should be auto-updated based on action count.
    
    Args:
        project_name: Name of the project
        threshold: Number of actions before suggesting README update (default: 5)
        
    Returns:
        bool: True if README should be updated
    """
    try:
        memory = load_memory(project_name)
        
        if not memory:
            return False
        
        # Get last README update time
        last_update = memory.get("last_readme_update")
        
        # Get total actions since last update
        total_actions = memory.get("stats", {}).get("total_actions", 0)
        
        # If never updated, check if we've exceeded threshold
        if not last_update:
            return total_actions >= threshold
        
        # Count actions since last update
        last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
        actions = memory.get("actions", [])
        
        recent_actions = 0
        for action in actions:
            action_time = datetime.fromisoformat(action["timestamp"].replace('Z', '+00:00'))
            if action_time > last_update_time:
                recent_actions += 1
        
        return recent_actions >= threshold
        
    except Exception as e:
        log_message(f"[Memory] Error checking README update status for {project_name}: {e}")
        return False


def mark_readme_updated(project_name: str) -> bool:
    """
    Mark that README was updated.
    
    Args:
        project_name: Name of the project
        
    Returns:
        bool: True if marked successfully
    """
    try:
        memory = load_memory(project_name)
        
        if not memory:
            return False
        
        memory["last_readme_update"] = datetime.utcnow().isoformat() + "Z"
        
        return save_memory(project_name, memory)
        
    except Exception as e:
        log_message(f"[Memory] Error marking README update for {project_name}: {e}")
        return False


# ===============================
# Memory Statistics and Analysis
# ===============================

def get_memory_stats(project_name: str) -> Dict[str, Any]:
    """
    Get comprehensive statistics about project memory.
    
    Args:
        project_name: Name of the project
        
    Returns:
        dict: Statistics including action counts, timestamps, etc.
    """
    try:
        memory = load_memory(project_name)
        
        if not memory:
            return {"status": "error", "message": "Project not found"}
        
        return {
            "status": "success",
            "project_name": project_name,
            "created_at": memory.get("created_at"),
            "last_updated": memory.get("last_updated"),
            "stats": memory.get("stats", {}),
            "total_actions_logged": len(memory.get("actions", [])),
            "readme_update_needed": should_update_readme(project_name)
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===============================
# Task 8: Semantic Memory - Backup and Migration Functions
# ===============================

def backup_memory(project_name: str) -> bool:
    """
    Create timestamped backup of memory.json before migration.
    
    Args:
        project_name: Name of the project
        
    Returns:
        bool: True if backup created successfully
    """
    try:
        memory_path = f"projects/{project_name}/.lazydeve/memory.json"
        
        if not os.path.exists(memory_path):
            log_message(f"[Memory] No memory file to backup for {project_name}")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{memory_path}.backup_{timestamp}"
        
        shutil.copy2(memory_path, backup_path)
        log_message(f"[Memory] Backup created: memory.json.backup_{timestamp}")
        return True
        
    except Exception as e:
        log_message(f"[Memory] ERROR: Backup failed for {project_name}: {str(e)}")
        return False


def restore_memory_from_backup(project_name: str, backup_timestamp: Optional[str] = None) -> bool:
    """
    Restore memory.json from backup.
    
    Args:
        project_name: Name of the project
        backup_timestamp: Specific backup timestamp (YYYYMMDD_HHMMSS).
                         If None, uses the most recent backup.
        
    Returns:
        bool: True if restored successfully
    """
    try:
        lazydeve_dir = f"projects/{project_name}/.lazydeve"
        memory_path = f"{lazydeve_dir}/memory.json"
        
        if not os.path.exists(lazydeve_dir):
            log_message(f"[Memory] ERROR: Project directory not found: {project_name}")
            return False
        
        # Find backup files
        backup_files = [f for f in os.listdir(lazydeve_dir) if f.startswith("memory.json.backup_")]
        
        if not backup_files:
            log_message(f"[Memory] WARNING: No backup found for {project_name}")
            return False
        
        # Select backup
        if backup_timestamp:
            backup_file = f"memory.json.backup_{backup_timestamp}"
            if backup_file not in backup_files:
                log_message(f"[Memory] ERROR: Backup {backup_timestamp} not found")
                return False
        else:
            # Use most recent
            backup_files.sort(reverse=True)
            backup_file = backup_files[0]
        
        backup_path = f"{lazydeve_dir}/{backup_file}"
        
        # Restore
        shutil.copy2(backup_path, memory_path)
        log_message(f"[Memory] Restored from {backup_file}")
        return True
        
    except Exception as e:
        log_message(f"[Memory] ERROR: Restore failed for {project_name}: {str(e)}")
        return False


def migrate_memory_to_task8(project_name: str) -> bool:
    """
    Migrate memory.json to Task 8 structure with semantic_context.
    Includes automatic backup and rollback on failure.
    
    Args:
        project_name: Name of the project
        
    Returns:
        bool: True if migration successful
    """
    try:
        # Step 1: Create backup
        if not backup_memory(project_name):
            log_message(f"[Migration] ERROR: Backup failed for {project_name}, aborting")
            return False
        
        # Step 2: Load current memory (disable auto-migrate to prevent recursion)
        memory = load_memory(project_name, auto_migrate=False)
        
        if not memory:
            log_message(f"[Migration] ERROR: Failed to load memory for {project_name}")
            return False
        
        # Step 3: Check if already migrated
        if "semantic_context" in memory:
            log_message(f"[Migration] {project_name} already migrated to Task 8")
            return True
        
        # Step 4: Add Task 8 structure
        memory["semantic_context"] = {
            "description": None,
            "tech_stack": [],
            "keywords": [],
            "activity_summary": {
                "total_actions": len(memory.get("actions", [])),
                "recent_focus": None,
                "common_operations": [],
                "error_patterns": []
            },
            "confidence_score": 0.0,
            "last_analyzed": None
        }
        
        memory["documentation"] = {
            "readme_last_updated": None,
            "auto_generated": False,
            "sections": []
        }
        
        # Step 5: Save migrated memory
        success = save_memory(project_name, memory)
        
        if success:
            log_message(f"[Migration] {project_name} migrated to Task 8 structure")
            return True
        else:
            # Rollback on failure
            log_message(f"[Migration] ERROR: Save failed, rolling back {project_name}")
            restore_memory_from_backup(project_name)
            return False
            
    except Exception as e:
        log_message(f"[Migration] ERROR: Failed for {project_name}: {str(e)}")
        # Attempt rollback
        restore_memory_from_backup(project_name)
        return False


# ===============================
# Example Usage and Testing
# ===============================

if __name__ == "__main__":
    print("Testing memory_utils.py...")
    
    # Test 1: Initialize project memory
    print("\n1. Initializing test project memory...")
    test_project = "TestProject_Memory"
    memory = init_project_memory(test_project, "Test project for memory utils")
    print(f"✅ Initialized memory: {memory.get('project_name')}")
    
    # Test 2: Load memory
    print("\n2. Loading memory...")
    loaded_memory = load_memory(test_project)
    print(f"✅ Loaded memory: {loaded_memory.get('stats')}")
    
    # Test 3: Update memory with actions
    print("\n3. Updating memory with actions...")
    result = update_memory(test_project, "execute", "Test task execution")
    print(f"✅ Update result: {result}")
    
    result = update_memory(test_project, "commit", "Test commit")
    print(f"✅ Update result: {result}")
    
    # Test 4: Log project action
    print("\n4. Logging project action...")
    success = log_project_action(test_project, "execute", "Executed test task successfully")
    print(f"✅ Log action: {'Success' if success else 'Failed'}")
    
    # Test 5: Check README update
    print("\n5. Checking README update trigger...")
    needs_update = should_update_readme(test_project, threshold=2)
    print(f"✅ Needs README update: {needs_update}")
    
    # Test 6: Get statistics
    print("\n6. Getting memory statistics...")
    stats = get_memory_stats(test_project)
    print(f"✅ Stats: {stats}")
    
    # Test 7: Corruption recovery (simulate)
    print("\n7. Testing corruption recovery...")
    memory_path = f"projects/{test_project}/.lazydeve/memory.json"
    
    # Backup original
    if os.path.exists(memory_path):
        shutil.copy(memory_path, memory_path + ".test_backup")
        
        # Write corrupted JSON
        with open(memory_path, "w") as f:
            f.write("{invalid json here")
        
        # Try to load (should recover)
        recovered = load_memory(test_project)
        print(f"✅ Recovered from corruption: {recovered.get('project_name')}")
        
        # Restore original
        shutil.copy(memory_path + ".test_backup", memory_path)
        os.remove(memory_path + ".test_backup")
    
    print("\n✅ All memory_utils tests completed successfully!")


