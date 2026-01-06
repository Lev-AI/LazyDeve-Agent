"""
log_manager.py
--------------
Unified JSON-based logging system for LazyDeve Agent.
Provides structured, thread-safe logging for semantic memory analysis.

All logs are written in JSON format for easy parsing and analysis in Task 8.
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional


class LogManager:
    """
    Centralized JSON-based logger with thread-safety and structured output.
    
    Features:
    - Thread-safe logging operations
    - JSON-formatted log entries
    - Project-based log organization
    - Extensible metadata support
    - Compatible with existing log_message() infrastructure
    
    Usage:
        logger = LogManager()
        logger.log("LazyDeve_Agent", "INFO", "Task executed successfully", 
                   extra={"action": "execute", "duration_ms": 1250})
    """
    
    _instance: Optional['LogManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure one logger instance across the application."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, base_dir: str = "logs"):
        """
        Initialize the LogManager.
        
        Args:
            base_dir: Base directory for log files (default: "logs")
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return
            
        self.base_dir = base_dir
        self._file_lock = threading.Lock()
        
        # Ensure log directory exists
        os.makedirs(base_dir, exist_ok=True)
        
        self._initialized = True
    
    def log(self, project: str, level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> bool:
        """
        Write a structured JSON log entry.
        
        Args:
            project: Project name (e.g., "LazyDeve_Agent", "MyProject")
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Human-readable log message
            extra: Optional dictionary with additional metadata
            
        Returns:
            bool: True if log was written successfully, False otherwise
            
        Example:
            logger.log("LazyDeve_Agent", "INFO", "File created",
                      extra={"path": "test.py", "size": 1024})
        """
        with self._file_lock:
            try:
                # Build log entry
                entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": level.upper(),
                    "project": project,
                    "message": message
                }
                
                # Add extra metadata if provided
                if extra and isinstance(extra, dict):
                    entry["extra"] = extra
                
                # Determine log file path
                log_path = os.path.join(self.base_dir, f"{project}.log")
                
                # Write JSON line to log file
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                
                return True
                
            except Exception as e:
                # Fallback to stderr if logging fails
                print(f"[LogManager] Failed to write log: {e}")
                return False
    
    def log_simple(self, project: str, level: str, message: str) -> bool:
        """
        Simplified logging method without extra metadata.
        
        This is used as a drop-in replacement for existing log_message() calls.
        
        Args:
            project: Project name
            level: Log level
            message: Log message
            
        Returns:
            bool: True if successful
        """
        return self.log(project, level, message, extra=None)
    
    def read_logs(self, project: str, lines: int = 100) -> list:
        """
        Read recent log entries for a project.
        
        Args:
            project: Project name
            lines: Number of recent lines to read (default: 100)
            
        Returns:
            list: List of parsed JSON log entries
        """
        with self._file_lock:
            try:
                log_path = os.path.join(self.base_dir, f"{project}.log")
                
                if not os.path.exists(log_path):
                    return []
                
                # Read last N lines
                with open(log_path, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                # Parse JSON entries
                parsed_logs = []
                for line in recent_lines:
                    line = line.strip()
                    if line:
                        try:
                            parsed_logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
                
                return parsed_logs
                
            except Exception as e:
                print(f"[LogManager] Failed to read logs: {e}")
                return []
    
    def get_stats(self, project: str) -> Dict[str, Any]:
        """
        Get statistics about a project's logs.
        
        Args:
            project: Project name
            
        Returns:
            dict: Statistics including count, levels, etc.
        """
        logs = self.read_logs(project, lines=1000)  # Analyze last 1000 entries
        
        if not logs:
            return {"total": 0, "levels": {}}
        
        # Count log levels
        level_counts = {}
        for entry in logs:
            level = entry.get("level", "UNKNOWN")
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            "total": len(logs),
            "levels": level_counts,
            "first_entry": logs[0].get("timestamp") if logs else None,
            "last_entry": logs[-1].get("timestamp") if logs else None
        }


# Global logger instance
_global_logger = None


def get_logger() -> LogManager:
    """
    Get the global LogManager instance.
    
    Returns:
        LogManager: Global logger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = LogManager()
    return _global_logger


# Convenience function for quick logging
def log(project: str, level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> bool:
    """
    Quick logging function using the global logger.
    
    Args:
        project: Project name
        level: Log level
        message: Log message
        extra: Optional metadata
        
    Returns:
        bool: True if successful
    """
    return get_logger().log(project, level, message, extra)


# Example usage and testing
if __name__ == "__main__":
    # Test the LogManager
    logger = LogManager()
    
    print("Testing LogManager...")
    
    # Test 1: Simple log
    logger.log("LazyDeve_Agent", "INFO", "LogManager initialized")
    
    # Test 2: Log with metadata
    logger.log("LazyDeve_Agent", "INFO", "Task executed successfully",
               extra={"action": "execute", "duration_ms": 1250, "status": "success"})
    
    # Test 3: Different log levels
    logger.log("LazyDeve_Agent", "WARNING", "High memory usage detected")
    logger.log("LazyDeve_Agent", "ERROR", "Failed to connect to database")
    logger.log("LazyDeve_Agent", "DEBUG", "Processing item 5 of 10")
    
    # Test 4: Read logs
    recent_logs = logger.read_logs("LazyDeve_Agent", lines=10)
    print(f"\n✅ Read {len(recent_logs)} log entries")
    
    # Test 5: Get stats
    stats = logger.get_stats("LazyDeve_Agent")
    print(f"✅ Log statistics: {stats}")
    
    print("\n✅ LogManager tests completed successfully!")


