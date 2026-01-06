"""
Event Logger - Persistent event history
✅ TASK 8.8: Event persistence layer
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from core.basic_functional import log_message
from core.memory_lock import safe_append_log


def log_event(
    project_name: str,
    event_type: str,
    details: Dict[str, Any] = None
) -> bool:
    """
    Log event to events.log file.
    
    ✅ TASK 8.8: Event persistence
    
    Args:
        project_name: Project name
        event_type: Event type (e.g., "run_logged", "commit_synced")
        details: Optional event details
    
    Returns:
        bool: True if logged successfully
    """
    try:
        # Ensure .lazydeve directory exists
        lazydeve_dir = f"projects/{project_name}/.lazydeve"
        os.makedirs(lazydeve_dir, exist_ok=True)
        
        events_log_path = f"projects/{project_name}/.lazydeve/events.log"
        
        event_entry = {
            "timestamp": datetime.now().isoformat() + "Z",
            "type": event_type,
            "details": details or {}
        }
        
        # Append JSON line to events.log
        log_line = json.dumps(event_entry, ensure_ascii=False) + "\n"
        safe_append_log(events_log_path, log_line, timestamp=False)
        
        # Rotate if too large (10MB or 1000 entries)
        _rotate_events_log(events_log_path)
        
        return True
        
    except Exception as e:
        log_message(f"[EventLogger] Failed to log event: {e}")
        return False


def read_events(
    project_name: str,
    event_type: str = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Read events from events.log.
    
    ✅ TASK 8.8: Event querying
    
    Args:
        project_name: Project name
        event_type: Filter by event type (optional)
        limit: Maximum number of events to return
    
    Returns:
        list: Event entries
    """
    try:
        events_log_path = f"projects/{project_name}/.lazydeve/events.log"
        
        if not os.path.exists(events_log_path):
            return []
        
        events = []
        with open(events_log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event_type and event.get("type") != event_type:
                        continue
                    events.append(event)
                except json.JSONDecodeError:
                    continue
        
        # Return most recent events first
        return events[-limit:] if len(events) > limit else events
        
    except Exception as e:
        log_message(f"[EventLogger] Error reading events: {e}")
        return []


def _rotate_events_log(events_log_path: str, max_size_mb: int = 10, max_entries: int = 1000):
    """Rotate events.log if too large."""
    try:
        if not os.path.exists(events_log_path):
            return
        
        # Check size
        size_mb = os.path.getsize(events_log_path) / (1024 * 1024)
        if size_mb > max_size_mb:
            # Keep last 500 entries
            _keep_last_entries(events_log_path, 500)
            return
        
        # Check entry count
        with open(events_log_path, "r", encoding="utf-8") as f:
            line_count = sum(1 for _ in f)
        
        if line_count > max_entries:
            _keep_last_entries(events_log_path, max_entries // 2)
            
    except Exception as e:
        log_message(f"[EventLogger] Rotation failed: {e}")


def _keep_last_entries(events_log_path: str, keep_count: int):
    """
    Keep only last N entries in events.log (atomic operation).
    ✅ TASK 8.8 COMPATIBILITY: Atomic rename prevents data loss
    """
    try:
        with open(events_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if len(lines) <= keep_count:
            return
        
        # Keep last N lines
        kept_lines = lines[-keep_count:]
        
        # ✅ TASK 8.8 COMPATIBILITY: Atomic rename prevents data loss during rotation
        temp_path = events_log_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.writelines(kept_lines)
        
        # Atomic replace
        os.replace(temp_path, events_log_path)
            
        log_message(f"[EventLogger] Rotated events.log: kept last {keep_count} entries")
        
    except Exception as e:
        log_message(f"[EventLogger] Failed to rotate: {e}")

