"""
system_protection.py
-------------------
System Protection Module for LazyDeve Agent.

This module provides comprehensive protection for core/root files and directories,
preventing accidental modification or deletion of critical system components.

Features:
- Root file protection
- Directory protection  
- Project context validation
- Operation auditing
- Backup and rollback system
- Configuration-based protection rules
"""

import os
import json
import shutil
import datetime
from typing import Dict, Any, List, Optional
from core.basic_functional import log_message

# ===============================
# Configuration Loading
# ===============================

def load_protection_rules() -> Dict[str, Any]:
    """
    Load protection rules from rules.json.
    Returns comprehensive protection configuration.
    """
    try:
        rules_path = os.path.join(os.path.dirname(__file__), "..", "rules.json")
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
        
        # Get core protection rules
        protection_rules = rules.get("core_protection_rules", {})
        
        # Enhanced protection configuration
        enhanced_rules = {
            "restricted_directories": protection_rules.get("restricted_directories", []),
            "protected_root_files": [
                "main.py", "agent.py", "requirements.txt", "README.md",
                "rules.json", "openai.yaml", "openai_full_schema.yaml",
                "tasks.md", ".env", ".gitignore", "Dockerfile", "docker-compose.yml"
            ],
            "protected_root_directories": [
                "core/", "docs/", "logs/", "tests/", "archive_files/"
            ],
            "protected_file_extensions": [
                ".py", ".json", ".yaml", ".yml", ".md", ".txt", ".env"
            ],
            "enforced": protection_rules.get("enforced", True),
            "backup_enabled": True,
            "audit_logging": True,
            "project_context_required": True
        }
        
        log_message(f"[SystemProtection] Loaded protection rules from: {os.path.abspath(rules_path)}")
        return enhanced_rules
        
    except Exception as e:
        log_message(f"[SystemProtection] Failed to load rules.json: {e}")
        # Return default protection rules
        return {
            "restricted_directories": ["core/", "projects/"],
            "protected_root_files": ["main.py", "agent.py", "rules.json"],
            "protected_root_directories": ["core/", "docs/", "logs/", "tests/"],
            "protected_file_extensions": [".py", ".json", ".yaml", ".md"],
            "enforced": True,
            "backup_enabled": True,
            "audit_logging": True,
            "project_context_required": True
        }

# ===============================
# Protection Validation
# ===============================

def is_protected_root_file(path: str, rules: Dict[str, Any]) -> bool:
    """
    Check if a file is protected from modification at root level.
    ✅ BUG-FIX 2: Normalize absolute paths before checking
    
    Args:
        path: File path to check
        rules: Protection rules configuration
        
    Returns:
        bool: True if file is protected
    """
    # ✅ BUG-FIX 2: Normalize path (handle absolute paths on Windows/Unix)
    normalized_path = path.replace("\\", "/")  # Windows path normalization
    
    # ✅ BUG-FIX 2: Check if path contains projects/ (works for both relative and absolute)
    # Examples:
    #   "projects/test/README.md" → contains "/projects/"
    #   "C:/Users/.../projects/test/README.md" → contains "/projects/"
    #   "/home/user/.../projects/test/README.md" → contains "/projects/"
    if "/projects/" in normalized_path or normalized_path.startswith("projects/"):
        return False  # File is in projects/ directory - not protected
    
    filename = os.path.basename(path)
    protected_files = rules.get("protected_root_files", [])
    
    # Check exact filename match
    if filename in protected_files:
        return True
    
    # Check file extension only for root-level files
    file_ext = os.path.splitext(filename)[1]
    protected_extensions = rules.get("protected_file_extensions", [])
    if file_ext in protected_extensions and not ("/projects/" in normalized_path or normalized_path.startswith("projects/")):
        return True
    
    return False

def is_protected_root_directory(path: str, rules: Dict[str, Any]) -> bool:
    """
    Check if a directory is protected from modification at root level.
    
    Args:
        path: Directory path to check
        rules: Protection rules configuration
        
    Returns:
        bool: True if directory is protected
    """
    protected_dirs = rules.get("protected_root_directories", [])
    
    for protected_dir in protected_dirs:
        if path.startswith(protected_dir):
            return True
    
    return False

def is_restricted_directory(path: str, rules: Dict[str, Any]) -> bool:
    """
    Check if a directory is in the restricted directories list.
    ✅ TASK 8.4: Hard block for core/, api/, utils/ directories
    
    Args:
        path: Directory path to check
        rules: Protection rules configuration
        
    Returns:
        bool: True if directory is restricted
    """
    if not path:
        return False
    
    # Normalize path for comparison
    normalized_path = path.replace("\\", "/").rstrip("/")
    
    # ✅ TASK 8.4: Hard block core/, api/, utils/ directories
    # These are ALWAYS restricted, regardless of rules.json
    hard_blocked_dirs = ["core/", "api/", "utils/"]
    for blocked_dir in hard_blocked_dirs:
        normalized_blocked = blocked_dir.replace("\\", "/").rstrip("/")
        if normalized_path.startswith(normalized_blocked) or normalized_path == normalized_blocked.rstrip("/"):
            from core.basic_functional import log_message
            log_message(f"[SECURITY] 🔒 HARD BLOCK: Attempted write to restricted directory: {path}")
            return True
    
    # Allow all operations within projects/ directory
    if path.startswith("projects/"):
        return False
    
    # Check other restricted directories from rules
    restricted_dirs = rules.get("restricted_directories", [])
    
    for restricted_dir in restricted_dirs:
        # Normalize restricted directory path
        normalized_restricted = restricted_dir.replace("\\", "/").rstrip("/")
        
        # Skip projects/ directory from restriction check
        if normalized_restricted.endswith("projects/") or normalized_restricted.endswith("projects"):
            continue
            
        # Check if path starts with restricted directory
        if normalized_path.startswith(normalized_restricted):
            return True
    
    return False

# ===============================
# Project Context Validation
# ===============================

def get_active_project_context() -> Dict[str, Any]:
    """
    Get the currently active project for context validation.
    Uses ContextManager singleton for consistent state management.
    
    Returns:
        dict: {"status": "success", "project": str} or {"status": "error", "message": str}
    """
    try:
        from core.context_manager import context_manager
        project = context_manager.get_active_project_context()
        if project:
            return {"status": "success", "project": project}
        else:
            return {"status": "error", "message": "No active project set"}
    except ImportError:
        # Fallback to legacy method if ContextManager not available
        # ❌ REMOVED: Root memory.json fallback (security fix - Task 8.8.2 Bug #1)
        # Use projects/.last_active_project instead
        try:
            last_active_file = "projects/.last_active_project"
            if os.path.exists(last_active_file):
                with open(last_active_file, "r", encoding="utf-8") as f:
                    project = f.read().strip()
                if project and os.path.exists(f"projects/{project}"):
                    return {"status": "success", "project": project}
                else:
                    return {"status": "error", "message": "No active project found"}
            else:
                return {"status": "error", "message": "No active project file found"}
        except Exception as e:
            from core.error_handler import handle_error
            return handle_error("system_protection", "get_active_project_context", e)
    except Exception as e:
        from core.error_handler import handle_error
        return handle_error("system_protection", "get_active_project_context", e)

def validate_project_context(path: str, operation: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that file operations are within the correct project context.
    
    Args:
        path: File path to validate
        operation: Operation being performed
        rules: Protection rules configuration
        
    Returns:
        dict: Validation result with status and details
    """
    if not rules.get("project_context_required", True):
        return {"status": "ok"}
    
    active_project_result = get_active_project_context()
    
    # Handle error from get_active_project_context
    if active_project_result.get("status") == "error":
        return active_project_result
    
    active_project = active_project_result.get("project")
    
    # Allow operations when no specific project is active (root operations)
    if not active_project or active_project == "default":
        return {"status": "ok"}
    
    # Check if path is within the active project
    expected_prefix = f"projects/{active_project}/"
    if not path.startswith(expected_prefix):
        return {
            "status": "error",
            "error": f"File operation outside active project context",
            "details": {
                "expected_prefix": expected_prefix,
                "actual_path": path,
                "active_project": active_project,
                "operation": operation
            },
            "suggestion": f"Use path: {expected_prefix}{os.path.basename(path)}"
        }
    
    return {"status": "ok"}

# ===============================
# Comprehensive Protection Check
# ===============================

def validate_file_operation(path: str, operation: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive validation of file operations against all protection rules.
    Uses smart protection that distinguishes between malicious and legitimate operations.
    
    Args:
        path: File path to validate
        operation: Operation being performed (create, update, delete, etc.)
        rules: Protection rules configuration
        
    Returns:
        dict: Validation result with status and details
    """
    # Check if protection is enforced
    if not rules.get("enforced", True):
        return {"status": "ok"}
    
    # SMART PROTECTION: Allow legitimate agent operations
    if _is_legitimate_agent_operation(path, operation):
        return {"status": "ok"}
    
    # 1. Check protected root files
    if is_protected_root_file(path, rules):
        return {
            "status": "error",
            "error": f"Protected root file cannot be {operation}",
            "details": {
                "path": path,
                "operation": operation,
                "protection_type": "root_file"
            },
            "suggestion": f"Use project-specific path: projects/<project_name>/{os.path.basename(path)}"
        }
    
    # 2. Check protected root directories
    if is_protected_root_directory(path, rules):
        return {
            "status": "error",
            "error": f"Protected root directory cannot be {operation}",
            "details": {
                "path": path,
                "operation": operation,
                "protection_type": "root_directory"
            },
            "suggestion": f"Use project-specific path: projects/<project_name>/<subdir>"
        }
    
    # 3. Check restricted directories
    if is_restricted_directory(path, rules):
        return {
            "status": "error",
            "error": f"Restricted directory cannot be {operation}",
            "details": {
                "path": path,
                "operation": operation,
                "protection_type": "restricted_directory"
            },
            "suggestion": f"Operation not allowed in restricted directory: {path}"
        }
    
    # 4. Validate project context
    context_check = validate_project_context(path, operation, rules)
    if context_check["status"] == "error":
        return context_check
    
    return {"status": "ok"}

def _is_legitimate_agent_operation(path: str, operation: str) -> bool:
    """
    Check if this is a legitimate agent operation that should be allowed.
    ✅ TASK 8.4: Removed core file exceptions - all core/ writes now blocked
    
    Args:
        path: File path
        operation: Operation being performed
        
    Returns:
        bool: True if this is a legitimate agent operation
    """
    # ❌ REMOVED (TASK 8.4): Core file exceptions (security risk)
    # if path in ["agent.py", "core/basic_functional.py", "core/system_protection.py"]:
    #     return True
    # Rationale: Hard block in is_restricted_directory() now prevents ALL core/, api/, utils/ writes
    
    # Allow agent to update configuration files (root level only)
    if path in ["rules.json", "openai.yaml", "openai_full_schema.yaml"]:
        return True
    
    # Allow agent to update documentation (root level only)
    if path in ["tasks.md", "README.md"]:
        return True
    
    # Allow agent to write logs
    if path.startswith("logs/") and operation in ["create", "update"]:
        return True
    
    # ❌ REMOVED: Root memory.json exception (security fix - Task 8.8.2 Bug #1)
    # Root memory.json creation is now blocked by protection system
    # Use projects/.last_active_project instead
    
    # Allow agent to update requirements
    if path in ["requirements.txt"]:
        return True
    
    # ✅ TASK 8.4: Only allow project files in active project
    active_project_result = get_active_project_context()
    if active_project_result.get("status") == "success":
        active_project = active_project_result.get("project")
        if active_project and path.startswith(f"projects/{active_project}/"):
            return True
    
    # Allow project creation (new projects)
    if path.startswith("projects/") and operation == "create":
        return True
    
    # Allow project management operations
    if path.startswith("projects/") and operation in ["update", "delete"]:
        return True
    
    # TEMPORARY: allow safe test operations (Task 7.7.4b)
    # Remove or tighten after full test cycle completion
    if path.startswith("tests/") and operation in ["read", "update"]:
        return True
    
    return False

def _is_malicious_overwrite(path: str, operation: str) -> bool:
    """
    Check if this is a malicious overwrite operation (like breathing app overwriting main.py).
    
    Args:
        path: File path
        operation: Operation being performed
        
    Returns:
        bool: True if this looks like a malicious overwrite
    """
    # Detect patterns that suggest malicious overwrite
    malicious_patterns = [
        # Breathing app overwriting main.py
        (path == "main.py" and "breathing" in str(operation).lower()),
        # Project files trying to overwrite root files
        (path in ["main.py", "agent.py"] and not _is_legitimate_agent_operation(path, operation)),
        # Files with suspicious names trying to overwrite core files
        (path in ["agent.py", "core/"] and "trainer" in str(operation).lower()),
    ]
    
    return any(malicious_patterns)

# ===============================
# Operation Auditing
# ===============================

def log_protection_event(event_type: str, path: str, success: bool, details: str = "", rules: Dict[str, Any] = None):
    """
    Log protection events for audit trail.
    
    Args:
        event_type: Type of event (BLOCKED, ALLOWED, BACKUP, etc.)
        path: File path involved
        success: Whether operation was successful
        details: Additional details
        rules: Protection rules used
    """
    if not rules or not rules.get("audit_logging", True):
        return
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "SUCCESS" if success else "BLOCKED"
    
    log_entry = f"[{timestamp}] PROTECTION {event_type.upper()} {status}: {path}"
    if details:
        log_entry += f" | {details}"
    
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/protection.log", "a", encoding="utf-8") as f:
            f.write(f"{log_entry}\n")
    except Exception as e:
        print(f"[SystemProtection] Failed to log protection event: {e}")

# ===============================
# Backup System
# ===============================

def create_protection_backup(path: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a timestamped backup of a file before modification.
    
    Args:
        path: File path to backup
        rules: Protection rules configuration
        
    Returns:
        dict: {"status": "success", "backup_path": str} or {"status": "error", "message": str}
    """
    if not rules.get("backup_enabled", True):
        return {"status": "success", "message": "Backup disabled", "backup_path": None}
    
    if not os.path.exists(path):
        return {"status": "error", "message": f"File not found: {path}"}
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.backup.{timestamp}"
    
    try:
        # Ensure backup directory exists
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)
        
        log_protection_event("BACKUP", path, True, f"Created backup: {backup_path}", rules)
        return {"status": "success", "backup_path": backup_path}
    except Exception as e:
        from core.error_handler import handle_error
        log_protection_event("BACKUP", path, False, f"Failed: {e}", rules)
        return handle_error("system_protection", "create_protection_backup", e, {"path": path})

def restore_from_backup(original_path: str, backup_path: str, rules: Dict[str, Any]) -> bool:
    """
    Restore a file from its backup.
    
    Args:
        original_path: Original file path
        backup_path: Backup file path
        rules: Protection rules configuration
        
    Returns:
        bool: True if restore was successful
    """
    try:
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, original_path)
            log_protection_event("RESTORE", original_path, True, f"Restored from: {backup_path}", rules)
            return True
        else:
            log_protection_event("RESTORE", original_path, False, f"Backup not found: {backup_path}", rules)
            return False
    except Exception as e:
        log_protection_event("RESTORE", original_path, False, f"Failed: {e}", rules)
        return False

# ===============================
# Main Protection Interface
# ===============================

def check_file_operation_protection(path: str, operation: str) -> Dict[str, Any]:
    """
    Main interface for checking file operation protection.
    
    Args:
        path: File path to check
        operation: Operation being performed
        
    Returns:
        dict: Protection check result
    """
    # Load protection rules
    rules = load_protection_rules()
    
    # Perform comprehensive validation
    validation_result = validate_file_operation(path, operation, rules)
    
    # Log the protection event
    if validation_result["status"] == "error":
        log_protection_event("BLOCKED", path, False, 
                           f"Reason: {validation_result['error']}", rules)
    else:
        log_protection_event("ALLOWED", path, True, f"Operation: {operation}", rules)
    
    return validation_result

def create_protected_backup(path: str, return_path_only: bool = False):
    """
    Create a backup with protection rules applied.
    
    TASK 8.1 FIX: Added return_path_only parameter for internal usage.
    
    Args:
        path: File path to backup
        return_path_only: If True, returns only the backup path string (for internal use).
                         If False, returns the full result dict (for API endpoints).
                         Default: False (maintains backward compatibility)
        
    Returns:
        If return_path_only=True: str (backup path) or None (on error)
        If return_path_only=False: dict (full API response with status, backup_path, etc.)
    """
    rules = load_protection_rules()
    result = create_protection_backup(path, rules)
    
    # If caller wants only the path string (internal usage)
    if return_path_only:
        if isinstance(result, dict):
            return result.get("backup_path", None)
        # Fallback: if result is already a string, return it
        return result if isinstance(result, str) else None
    
    # Default: return full dict (API usage)
    return result

# ===============================
# Utility Functions
# ===============================

def get_protection_status() -> Dict[str, Any]:
    """
    Get current protection system status and configuration.
    
    Returns:
        dict: Protection system status
    """
    rules = load_protection_rules()
    active_project_result = get_active_project_context()
    
    # Extract active project safely
    active_project = None
    if active_project_result.get("status") == "success":
        active_project = active_project_result.get("project")
    
    return {
        "protection_enabled": rules.get("enforced", True),
        "backup_enabled": rules.get("backup_enabled", True),
        "audit_logging": rules.get("audit_logging", True),
        "project_context_required": rules.get("project_context_required", True),
        "active_project": active_project,
        "protected_root_files": len(rules.get("protected_root_files", [])),
        "protected_root_directories": len(rules.get("protected_root_directories", [])),
        "restricted_directories": len(rules.get("restricted_directories", [])),
        "rules_source": "rules.json"
    }

def list_protected_files() -> List[str]:
    """
    List all currently protected files and directories.
    
    Returns:
        list: List of protected paths
    """
    rules = load_protection_rules()
    protected_items = []
    
    # Add protected root files
    protected_items.extend(rules.get("protected_root_files", []))
    
    # Add protected root directories
    protected_items.extend(rules.get("protected_root_directories", []))
    
    # Add restricted directories
    protected_items.extend(rules.get("restricted_directories", []))
    
    return protected_items


def log_security_event(event_type: str, path: str, operation: str, blocked: bool, reason: str = ""):
    """
    Log security events for audit trail.
    ✅ TASK 8.4: Security audit logging
    
    Args:
        event_type: Type of security event (e.g., "file_operation", "endpoint_isolation")
        path: Path involved in the event
        operation: Operation attempted (e.g., "create", "update", "delete")
        blocked: Whether the operation was blocked (True) or allowed (False)
        reason: Reason for blocking or allowing (optional)
    """
    from datetime import datetime
    from core.basic_functional import log_message
    
    timestamp = datetime.now().isoformat()
    status = "BLOCKED" if blocked else "ALLOWED"
    
    # Log to main agent log
    log_message(f"[SECURITY_AUDIT] {timestamp} | {status} | {event_type} | {operation} | {path} | Reason: {reason}")
    
    # Also write to dedicated security audit log file
    try:
        audit_log_path = "logs/security_audit.log"
        os.makedirs(os.path.dirname(audit_log_path), exist_ok=True)
        with open(audit_log_path, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {status} | {event_type} | {operation} | {path} | {reason}\n")
    except Exception as e:
        log_message(f"[SECURITY_AUDIT] Failed to write to security audit log: {e}")
