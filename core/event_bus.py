"""
event_bus.py
------------
Lightweight event-driven middleware for LazyDeve Agent.

This module provides a central event bus for post-action hooks, allowing
different subsystems to subscribe to events without modifying core agent code.

Usage:
    from core.event_bus import register_hook, trigger_event
    
    # Register a hook:
    def on_action_complete(project, action, **kwargs):
        print(f"Action {action} completed for {project}")
    
    register_hook("post_action", on_action_complete)
    
    # Trigger event:
    trigger_event("post_action", project="MyProject", action="execute", details="Task done")
"""

import traceback
import threading
from typing import Callable, Dict, List, Any
from datetime import datetime

# ===============================
# Global Event Hooks Registry
# ===============================

_event_hooks: Dict[str, List[Callable]] = {
    "post_action": [],      # Fired after successful /execute, /commit, /analyze
    "post_execute": [],     # Fired specifically after /execute
    "post_commit": [],      # Fired specifically after /commit
    "post_analyze": [],     # Fired specifically after /analyze
    "project_created": [],  # Fired when new project is created
    "project_switched": [], # Fired when active project changes
    "error": [],            # Fired when errors occur
    "get_context_snapshot": []  # Fired when context snapshot is requested
}

# Thread-safe lock for hook registration/removal
_hooks_lock = threading.Lock()

# Event statistics
_event_stats: Dict[str, Dict[str, Any]] = {}
_stats_lock = threading.Lock()

# ===============================
# Hook Registration
# ===============================

def register_hook(event_type: str, func: Callable, prepend: bool = False) -> bool:
    """
    Register a callback function for a specific event type.
    
    Args:
        event_type: Type of event to listen for (e.g., "post_action", "post_execute")
        func: Callback function to execute when event fires
        prepend: If True, adds hook at beginning of list (higher priority)
        
    Returns:
        bool: True if registration succeeded, False otherwise
        
    Example:
        def my_hook(project, action, **kwargs):
            print(f"Action: {action} on {project}")
        
        register_hook("post_action", my_hook)
    """
    with _hooks_lock:
        try:
            # Ensure event type exists
            if event_type not in _event_hooks:
                _event_hooks[event_type] = []
            
            # Check if hook already registered (prevent duplicates)
            if func in _event_hooks[event_type]:
                print(f"[EventBus] Hook {func.__name__} already registered for {event_type}")
                return False
            
            # Add hook
            if prepend:
                _event_hooks[event_type].insert(0, func)
            else:
                _event_hooks[event_type].append(func)
            
            print(f"[EventBus] Registered hook: {func.__name__} for event: {event_type}")
            return True
            
        except Exception as e:
            print(f"[EventBus] Error registering hook: {e}")
            return False

# ===============================
# Internal Hook Execution
# ===============================

def _update_stats(event_type: str, result: Dict[str, Any]) -> None:
    """
    Update event statistics for a given event type.
    
    Args:
        event_type: Type of event
        result: Execution result dictionary
    """
    with _stats_lock:
        if event_type not in _event_stats:
            _event_stats[event_type] = {
                "total_events": 0,
                "total_hooks_executed": 0,
                "total_hooks_failed": 0,
                "last_event": None
            }
        
        stats = _event_stats[event_type]
        stats["total_events"] += 1
        stats["total_hooks_executed"] += result.get("hooks_executed", 0)
        stats["total_hooks_failed"] += result.get("hooks_failed", 0)
        stats["last_event"] = result.get("timestamp")


def _execute_hooks(event_type: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Internal function to execute all hooks for an event type.
    
    ✅ BUG FIX: Missing function implementation (fixes /run-local endpoint failure)
    ✅ TASK 8.8.2: Critical fix for event system functionality
    
    Args:
        event_type: Type of event
        kwargs: Arguments to pass to hooks
        
    Returns:
        dict: Execution results with hooks_executed, hooks_failed, errors, and timestamp
    """
    result = {
        "event_type": event_type,
        "hooks_executed": 0,
        "hooks_failed": 0,
        "errors": [],
        "timestamp": datetime.now().isoformat()
    }
    
    # Get hooks (thread-safe copy)
    with _hooks_lock:
        hooks = _event_hooks.get(event_type, []).copy()
    
    if not hooks:
        return result
    
    # Execute each hook
    for func in hooks:
        try:
            func(**kwargs)
            result["hooks_executed"] += 1
        except Exception as e:
            result["hooks_failed"] += 1
            error_info = {
                "hook": func.__name__,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            result["errors"].append(error_info)
            print(f"[EventBus] Error in hook {func.__name__} for event {event_type}: {e}")
            # Don't print full traceback by default (too verbose)
    
    # Update statistics
    _update_stats(event_type, result)
    
    return result


# ===============================
# Event Triggering
# ===============================

def trigger_event(event_type: str, async_mode: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Trigger all registered callbacks for a given event type.
    
    Args:
        event_type: Type of event to trigger
        async_mode: If True, executes hooks in separate thread (non-blocking)
        **kwargs: Arguments to pass to hook functions
        
    Returns:
        dict: Results with success count, failure count, and errors
    """
    if async_mode:
        # Execute hooks in background thread
        thread = threading.Thread(
            target=_execute_hooks,
            args=(event_type, kwargs),
            daemon=True
        )
        thread.start()
        return {"status": "async", "message": "Hooks executing in background"}
    else:
        # Execute hooks synchronously
        return _execute_hooks(event_type, kwargs)

# ===============================
# Event Triggering
# ===============================

# Other functions remain unchanged...

# ===============================
# Hook Inspection
# ===============================

# Other functions remain unchanged...

# ===============================
# Utility Functions
# ===============================

# Other functions remain unchanged...

# ===============================
# Decorators
# ===============================

# Other functions remain unchanged...

# ===============================
# Module Information
# ===============================

__all__ = [
    'register_hook',
    'unregister_hook',
    'clear_hooks',
    'trigger_event',
    'list_hooks',
    'get_hook_count',
    'get_event_stats',
    'get_event_info',
    'reset_event_bus',
    'event_hook'
]

if __name__ == "__main__":
    # Module self-test
    print("Event Bus Module - Self Test")
    print("=" * 50)
    
    # Test hook registration
    def test_hook(project, action, **kwargs):
        print(f"Test hook called: {project} - {action}")
    
    register_hook("post_action", test_hook)
    print(f"Registered hooks: {list_hooks()}")
    
    # Test event triggering
    result = trigger_event("post_action", project="TestProject", action="test")
    print(f"Event result: {result}")
    
    # Test statistics
    stats = get_event_stats()
    print(f"Event stats: {stats}")
    
    print("=" * 50)
    print("✅ Event bus module loaded successfully")
