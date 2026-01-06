"""
basic_functional.py
-------------------
Core utility and support layer for LazyDeve Agent.
Handles logging, file operations, and base-level environment setup.

All comments and docstrings are in English.
"""

import os
import json
import datetime
import asyncio
import subprocess
from typing import Dict, Any, List

from core.context_manager import load_context, save_context, validate_context, get_context_summary, update_context_after_sync
from core.memory_lock import memory_lock, safe_read_json, safe_write_json, safe_append_log

# ===============================
# Logging Utilities
# ===============================

def log_message(message: str, log_path: str = "logs/agent.log") -> None:
    """
    Append a timestamped message to the agent log file.
    
    Now delegates to the unified LogManager for structured JSON logging,
    while maintaining backward compatibility with existing plaintext format.

    Args:
        message (str): The message to log.
        log_path (str): The path to the log file.
    """
    try:
        # Legacy plaintext format (for backward compatibility)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
        
        # New JSON-based logging (for semantic memory)
        try:
            from core.log_manager import get_logger
            logger = get_logger()
            
            # Extract project name from log_path or use default
            project_name = "LazyDeve_Agent"
            if "projects/" in log_path:
                # Extract project name from path like "projects/MyProject/logs/actions.log"
                parts = log_path.split("projects/")
                if len(parts) > 1:
                    project_parts = parts[1].split("/")
                    if project_parts:
                        project_name = project_parts[0]
            
            # Determine log level from message content
            level = "INFO"
            if any(keyword in message.lower() for keyword in ["error", "failed", "exception"]):
                level = "ERROR"
            elif any(keyword in message.lower() for keyword in ["warning", "warn"]):
                level = "WARNING"
            elif "[Agent]" in message or "[LazyDeve]" in message:
                level = "INFO"
            
            # Log to unified JSON format
            logger.log_simple(project_name, level, message)
            
        except Exception as json_log_error:
            # If JSON logging fails, continue with plaintext (graceful degradation)
            pass
            
    except Exception as e:
        print(f"[log_message] Failed to write log: {e}")


# ===============================
# File Operations
# ===============================

def read_file(path: str) -> Dict[str, Any]:
    """
    Read a file and return its content.

    Args:
        path (str): The path to the file.

    Returns:
        dict: A dictionary containing file metadata and content.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "content": content, "path": path}
    except FileNotFoundError:
        return {"status": "error", "error": f"File not found: {path}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def update_file(path: str, content: str, auto_sync: bool = True) -> Dict[str, Any]:
    """
    Overwrite a file with new content - with comprehensive protection checks.
    Task 7.7.11-B Enhanced - Added auto-sync to GitHub option.
    🔒 CRITICAL FIX: Auto-prefix paths with active project directory.

    Args:
        path (str): The path to the file.
        content (str): The new file content.
        auto_sync (bool): Automatically commit and push to GitHub (default: True).

    Returns:
        dict: A status message with sync_status and details.
    """
    # 🔒 CRITICAL FIX: Auto-prefix path with active project
    from core.context_manager import context_manager
    active_project = context_manager.get_project()
    
    if active_project and not path.startswith("projects/"):
        # Auto-prefix with project directory
        original_path = path
        path = os.path.join("projects", active_project, path)
        log_message(f"[PROTECTION] Auto-prefixed path: {original_path} → {path}")
    
    # 🔒 TASK 1 FIX: Explicit root README.md protection
    if path == "README.md" and not path.startswith("projects/"):
        return {
            "status": "error",
            "error": "Cannot update root README.md",
            "suggestion": f"Use project-specific README: projects/{active_project}/README.md" if active_project else "Set an active project first",
            "protection_type": "root_readme_protected"
        }
    
    # Import protection system
    from core.system_protection import check_file_operation_protection, create_protected_backup
    
    # Check protection rules
    protection_check = check_file_operation_protection(path, "update")
    if protection_check["status"] == "error":
        log_message(f"PROTECTION BLOCKED: {protection_check['error']}")
        return {
            "status": "error", 
            "error": protection_check["error"],
            "suggestion": protection_check.get("suggestion", ""),
            "protection_type": "file_operation_blocked"
        }
    
    # Create backup before modification
    backup_path = create_protected_backup(path)
    
    # TASK 8.1 FIX: Defensive type handling for backup_path
    # create_protected_backup() may return dict (API response) or string (path only)
    if isinstance(backup_path, dict):
        backup_path = backup_path.get("backup_path", None)
        log_message(f"[TASK 8.1] Extracted backup_path from dict: {backup_path}")
    
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        log_message(f"File updated: {path}")
        
        # ✅ TASK 3.6.1: Auto-sync file to GitHub with per-project Git context
        sync_status = "disabled"
        sync_details = {}
        
        if auto_sync:
            try:
                from utils.git_utils import safe_git_add, safe_git_commit, safe_git_push
                from core.config import allow_github_access
                import re
                import subprocess
                
                # Extract project name from path
                project_match = re.search(r'projects/([^/]+)', path)
                if not project_match:
                    log_message(f"[update_file] Cannot auto-commit: Path not in project directory")
                    sync_status = "skipped"
                    sync_details["reason"] = "not_in_project"
                else:
                    project_name = project_match.group(1)
                    project_path = f"projects/{project_name}"
                    
                    # ✅ TASK 4.2.3: Auto-create GitHub repo for existing projects if missing
                    # (Refactored to use reusable helper function)
                    if allow_github_access:
                        from utils.github_api import ensure_github_remote_exists
                        remote_result = ensure_github_remote_exists(project_name, project_path)
                        if remote_result["status"] == "created":
                            log_message(f"[update_file] ✅ GitHub repo auto-created and linked: {remote_result['repo_url']}")
                        elif remote_result["status"] == "linked":
                            log_message(f"[update_file] ✅ Linked existing GitHub repo: {remote_result['repo_url']}")
                        elif remote_result["status"] == "error":
                            log_message(f"[update_file] ⚠️ Auto-GitHub creation failed: {remote_result.get('error', '')}")
                    
                    # ✅ TASK 3.6.1: Use safe_git_* utilities with project context
                    # Add all changes (including .lazydeve/ updates)
                    add_result = safe_git_add(cwd=project_path)
                    
                    if add_result["status"] == "success":
                        log_message(f"[update_file] Git add successful for '{path}'")
                        sync_details["git_add"] = "success"
                        
                        # Git commit with descriptive message
                        file_name = os.path.basename(path)
                        commit_msg = f"chore: Update {file_name}"
                        commit_result = safe_git_commit(commit_msg, cwd=project_path)
                        
                        if commit_result["status"] == "success":
                            log_message(f"[update_file] Git commit successful: {commit_msg}")
                            sync_details["git_commit"] = "success"
                            
                            # ✅ TASK 4.2 FIX: Only push if allow_github_access=true
                            if allow_github_access:
                                # Git push (local-only if no remote)
                                push_result = safe_git_push(branch="main", cwd=project_path)
                                
                                if push_result["status"] == "success":
                                    log_message(f"[update_file] Git push successful for '{path}'")
                                    sync_details["git_push"] = "success"
                                    sync_status = "synced"
                                elif "no remote" in push_result.get("error", "").lower():
                                    log_message(f"[update_file] Local commit successful (no remote configured)")
                                    sync_details["git_push"] = "skipped_no_remote"
                                    sync_status = "committed_locally"  # ✅ Success even without remote
                                else:
                                    log_message(f"[update_file] Git push failed: {push_result.get('error', '')}")
                                    sync_details["git_push"] = "failed"
                            else:
                                # GitHub access disabled - local commit only
                                log_message(f"[update_file] Local commit successful (GitHub access disabled)")
                                sync_details["git_push"] = "skipped_github_disabled"
                                sync_status = "committed_locally"
                                sync_status = "partial"
                        else:
                            log_message(f"[update_file] Git commit info: {commit_result.get('message', '')}")
                            sync_details["git_commit"] = "no_changes"
                            sync_status = "no_changes"
                    else:
                        log_message(f"[update_file] Git add failed: {add_result.get('error', '')}")
                        sync_details["git_add"] = "failed"
                        sync_details["add_error"] = add_result.get("error", "")
                        sync_status = "failed"
                    
            except subprocess.TimeoutExpired:
                log_message(f"[update_file] Git operation timed out for '{path}'")
                sync_status = "timeout"
                sync_details["error"] = "Git operation timed out"
            except Exception as git_error:
                log_message(f"[update_file] Git auto-sync error: {git_error}")
                sync_status = "error"
                sync_details["error"] = str(git_error)
        
        # Task 7.7.11-B Enhanced — Event Bus & Memory Hooks Integration
        try:
            from core.event_bus import trigger_event
            from core.memory_utils import update_memory, log_project_action
            from core.context_manager import context_manager
            import re
            
            # Extract project name from path
            project_match = re.search(r'projects/([^/]+)', path)
            project_name = project_match.group(1) if project_match else None  # 🔒 TASK 1 FIX: No default
            
            # Get active project if available
            active_project = context_manager.get_project()
            if active_project:
                project_name = active_project
            elif not project_name:
                # If no project found in path and no active project, skip memory update
                project_name = None
            
            # Determine action type
            is_test = "test" in path.lower()
            action_type = "add_test" if is_test else "update_file"
            
            # Log action to project log
            log_project_action(project_name, action_type, f"File updated: {path[:80]}")
            
            # Update project memory
            update_memory(
                project_name,
                action_type,
                f"Updated: {os.path.basename(path)}",
                extra={
                    "path": path,
                    "file_type": "test" if is_test else "source",
                    "sync_status": sync_status
                }
            )
            
            # Trigger post_action event
            trigger_event(
                "post_action",
                async_mode=True,
                project=project_name,
                action=action_type,
                details=f"File update: {path}",
                success=True,
                sync_status=sync_status
            )
            
            # Trigger file_updated event
            trigger_event(
                "file_updated",
                async_mode=True,
                project=project_name,
                path=path,
                file_type="test" if is_test else "source",
                sync_status=sync_status
            )
            
            log_message(f"[update_file] Event hooks and memory updated for '{path}'")
            
        except Exception as hook_error:
            # Don't fail file update if event/memory hooks fail
            log_message(f"[update_file] Event/memory hook error (non-critical): {hook_error}")
        
        return {
            "status": "success", 
            "path": path,
            "backup": backup_path,
            "sync_status": sync_status,
            "sync_details": sync_details
        }
        
    except Exception as e:
        # Restore from backup if operation failed
        # TASK 8.1 FIX: Type-safe backup path check
        if isinstance(backup_path, (str, bytes, os.PathLike)) and os.path.exists(backup_path):
            from core.system_protection import restore_from_backup, load_protection_rules
            rules = load_protection_rules()
            restore_from_backup(path, backup_path, rules)
            log_message(f"Restored from backup: {backup_path}")
        elif backup_path:
            log_message(f"[TASK 8.1] Warning: backup_path has invalid type: {type(backup_path)}")
        return {"status": "error", "error": str(e)}


def create_file(path: str, content: str) -> Dict[str, Any]:
    """
    Create a new file with specified content - with comprehensive protection checks.
    🔒 CRITICAL FIX: Auto-prefix paths with active project directory.

    Args:
        path (str): The path to the file.
        content (str): The content to write to the file.

    Returns:
        dict: A status message.
    """
    # 🔒 CRITICAL FIX: Auto-prefix path with active project
    from core.context_manager import context_manager
    active_project = context_manager.get_project()
    
    if active_project and not path.startswith("projects/"):
        # Auto-prefix with project directory
        original_path = path
        path = os.path.join("projects", active_project, path)
        log_message(f"[PROTECTION] Auto-prefixed path: {original_path} → {path}")
    
    # Import protection system
    from core.system_protection import check_file_operation_protection
    
    # Check protection rules
    protection_check = check_file_operation_protection(path, "create")
    if protection_check["status"] == "error":
        log_message(f"PROTECTION BLOCKED: {protection_check['error']}")
        return {
            "status": "error", 
            "error": protection_check["error"],
            "suggestion": protection_check.get("suggestion", ""),
            "protection_type": "file_operation_blocked"
        }
    
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        log_message(f"File created: {path}")
        return {"status": "success", "path": path}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def append_to_file(path: str, content: str) -> Dict[str, Any]:
    """
    Append content to an existing file.

    Args:
        path (str): The path to the file.
        content (str): The content to append.

    Returns:
        dict: A status message.
    """
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n{content}")
        log_message(f"Appended to file: {path}")
        return {"status": "success", "path": path}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ===============================
# Other functions remain unchanged
# ===============================

# ===============================
# Directory Initialization
# ===============================

def init_environment() -> None:
    """
    Ensure that all essential directories exist.
    """
    for folder in ["logs", "projects", "core"]:
        os.makedirs(folder, exist_ok=True)
    log_message("Environment initialized successfully.")


def analyze_commit_structure() -> Dict[str, Any]:
    """
    Analyze the recent commit structure and summarize repository state.

    Returns:
        dict: A summary of the last 5 commits, modified files, and sync status.
    """
    try:
        # Get the last 5 commits
        commits = subprocess.run(
            ["git", "log", "-n", "5", "--pretty=format:%h - %s (%an, %ar)"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split('\n')

        # Get modified files in the last commit
        modified_files = subprocess.run(
            ["git", "diff", "--name-only", "HEAD^", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split('\n')

        # Check sync status
        local_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        remote_hash = subprocess.run(
            ["git", "ls-remote", "origin", "-h", "refs/heads/main"],
            capture_output=True, text=True, check=True
        ).stdout.split()[0]

        sync_status = "Synced" if local_hash == remote_hash else "Not Synced"

        return {
            "last_commits": commits,
            "modified_files": modified_files,
            "sync_status": sync_status
        }

    except Exception as e:
        log_message(f"[analyze_commit_structure] Error: {e}")
        return {"status": "error", "message": str(e)}


# ===============================
# Aider Task Execution
# ===============================

async def run_aider_task_async(prompt: str, model: str = "gpt-4o-mini", files: list = None, project: str = None):
    """
    Execute natural language tasks via Aider CLI asynchronously.
    Cloudflare-compatible non-blocking subprocess execution.
    
    🔒 CRITICAL PROTECTION: Aider confined to active project directory only.
    
    Args:
        prompt (str): The task description for Aider
        model (str): The LLM model to use (default: gpt-4o-mini)
        files (list): Optional list of specific files to include
        project (str): Optional project name (defaults to active project)
        
    Returns:
        dict: Result dictionary with status, returncode, stdout, and stderr
    """
    if files is None:
        files = []

    try:
        # 🔒 LAYER 1: Get active project context
        from core.context_manager import context_manager
        active_project = project or context_manager.get_project()
        
        # 🔒 CRITICAL: NO EXECUTION without project context
        if not active_project:
            log_message("[PROTECTION] ❌ BLOCKED: No active project set for Aider execution")
            return {
                "status": "error",
                "error": "PROTECTION: No active project selected",
                "message": "You must set an active project before using /execute. Use /projects/set-active/{name}",
                "suggestion": "Call /projects/list to see available projects, then /projects/set-active/{name}",
                "protection_reason": "Aider execution requires project context to prevent root directory modifications"
            }
        
        # 🔒 LAYER 2: Validate project exists
        project_dir = os.path.join("projects", active_project)
        if not os.path.exists(project_dir):
            log_message(f"[PROTECTION] ❌ BLOCKED: Project directory not found: {project_dir}")
            return {
                "status": "error",
                "error": f"Project directory not found: {project_dir}",
                "message": f"Project '{active_project}' does not exist",
                "suggestion": "Use /projects/list to see available projects"
            }
        
        # 🔒 TASK 3 FIX: Enhance prompt with explicit path constraints (preserve project context)
        # Get absolute project directory for clarity
        project_dir_abs = os.path.abspath(project_dir)
        
        # Enhance prompt with explicit path constraints while preserving project context
        # This addresses the root cause (path manipulation) while keeping context
        path_constraints = f"""

🔒 CRITICAL PATH CONSTRAINTS:
- Working directory: {project_dir_abs}
- Active project: {active_project}
- All file operations MUST be within: {project_dir_abs}
- DO NOT use absolute paths (C:\\... or /...)
- DO NOT use parent directory references (../ or ..\\)
- DO NOT create folders outside: {project_dir_abs}
- Use relative paths only (e.g., "src/main.py", not "../main.py" or "C:\\...")
- Current working directory is: {project_dir_abs}
"""
        
        # Preserve original prompt but add constraints (keeps project context)
        enhanced_prompt = f"{prompt}\n{path_constraints}"
        
        # Build Aider command with enhanced prompt
        # ✅ BUG-FIX 1: Removed deprecated --git-repo flag (removed in Aider ≥ v0.40.x)
        # Git context is automatically detected via cwd=project_dir parameter
        cmd = [
            "aider",
            "--yes",
            "--no-gitignore",
            # Removed: "--git-repo", project_dir_abs,  # Deprecated in Aider ≥ v0.40.x
            "--message", enhanced_prompt,  # Enhanced prompt with constraints
            "--model", model,
        ] + files

        log_message(f"[LazyDeve] Executing via Aider (async): {prompt[:100]}...")
        log_message(f"[PROTECTION] ✅ Aider confined to project: {active_project}")
        log_message(f"[PROTECTION] Working directory: {project_dir_abs}")
        log_message(f"[PROTECTION] Git repository: {project_dir_abs}/.git (per-project)")
        log_message(f"[PROTECTION] ⚠️ Warning: Aider can use absolute paths to escape cwd")
        log_message(f"[PROTECTION] Post-execution validation will check for root folder violations")
        
        # 🔒 LAYER 3: Create async subprocess with PROJECT working directory
        # CRITICAL: cwd=project_dir prevents root directory modifications!
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_dir  # 🔒 FORCE PROJECT DIRECTORY - CRITICAL PROTECTION!
        )
        
        # Wait for completion with timeout
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            log_message(f"[LazyDeve] Aider execution timed out after 60 seconds")
            return {
                "status": "error",
                "message": "Aider execution timed out",
                "returncode": -1,
                "stdout": "",
                "stderr": "Process timed out after 60 seconds"
            }

        stdout_str = stdout.decode(errors="ignore")
        stderr_str = stderr.decode(errors="ignore")

        # ✅ TASK 3.4: Log exit code for debugging
        log_message(f"[Aider] Exit code: {process.returncode}")
        
        # Log the result with detailed output
        if process.returncode == 0:
            log_message(f"[LazyDeve] Aider execution successful (async)")
            log_message(f"[Aider] Success output (first 200 chars): {stdout_str[:200]}")
        else:
            log_message(f"[LazyDeve] Aider execution failed with return code: {process.returncode}")
            log_message(f"[Aider] Error output: {stderr_str[:500]}")  # Show first 500 chars of error

        # 🔒 LAYER 4: Post-execution validation - check for root violations
        validation_result = await validate_aider_output_async()
        if validation_result["status"] == "violation":
            log_message(f"[PROTECTION] ⚠️ ROOT VIOLATION DETECTED AND REVERTED: {validation_result['files_reverted']}")
            # Continue with execution but log the violation
        
        # ✅ TASK 3.6.1: Auto-commit and push after Aider run (async) with project context
        try:
            # Git add - from project directory
            add_process = await asyncio.create_subprocess_exec(
                "git", "add", "-A",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir  # 🔒 Git operations in project context
            )
            await add_process.wait()
            
            # ✅ TASK 3.6.1: Git commit with project context
            commit_msg = f"[LazyDeve] auto: {prompt[:60]}..."
            commit_process = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", commit_msg,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir  # ✅ FIXED: Added cwd parameter
            )
            await commit_process.wait()
            
            # ✅ TASK 3.6.1: Git push with project context
            push_process = await asyncio.create_subprocess_exec(
                "git", "push",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir  # ✅ FIXED: Added cwd parameter
            )
            await push_process.wait()
            
            log_message(f"[LazyDeve] Aider task committed to {project_dir} (async): {commit_msg}")
        except Exception as commit_error:
            log_message(f"[LazyDeve] Auto-commit failed (async): {commit_error}")

        return {
            "status": "success",
            "returncode": process.returncode,
            "stdout": stdout_str[-1000:] if stdout_str else "",
            "stderr": stderr_str[-500:] if stderr_str else "",
        }

    except Exception as e:
        log_message(f"[run_aider_task_async] Error: {e}")
        return {"status": "error", "message": str(e)}


async def validate_aider_output_async() -> Dict[str, Any]:
    """
    🔒 LAYER 4: Post-execution validation
    Check if Aider modified any root-level protected files and auto-revert.
    
    Returns:
        dict: Validation result with status and reverted files
    """
    import datetime
    
    protected_root_files = [
        "main.py", "agent.py", "README.md", "rules.json",
        "openai.yaml", "openai_full_schema.yaml", "tasks.md", 
        ".env", ".gitignore", "Dockerfile", "docker-compose.yml"
    ]
    
    violations = []
    try:
        for file in protected_root_files:
            if os.path.exists(file):
                # Check if file was modified recently (within last 2 minutes)
                mtime = os.path.getmtime(file)
                current_time = datetime.datetime.now().timestamp()
                if (current_time - mtime) < 120:  # Modified in last 2 minutes
                    violations.append(file)
        
        # 🔒 TASK 3 FIX: Check for new folders in root directory
        root_dir = os.getcwd()
        projects_dir = os.path.join(root_dir, "projects")
        
        # Allowed root directories (system directories)
        allowed_root_dirs = ["core", "tests", "logs", "docs", "archive_files", 
                             "__pycache__", ".git", "projects", "api", "services",
                             "aarchive_files", "aarchive_files_2"]
        
        # Get list of directories in root
        root_dirs = []
        try:
            for d in os.listdir(root_dir):
                dir_path = os.path.join(root_dir, d)
                if os.path.isdir(dir_path) and d not in allowed_root_dirs:
                    root_dirs.append(d)
        except Exception as list_error:
            log_message(f"[PROTECTION] Error listing root directories: {list_error}")
        
        # Check if any new folders were created in last 2 minutes
        folder_violations = []
        for dir_name in root_dirs:
            dir_path = os.path.join(root_dir, dir_name)
            if os.path.exists(dir_path):
                try:
                    mtime = os.path.getmtime(dir_path)
                    current_time = datetime.datetime.now().timestamp()
                    if (current_time - mtime) < 120:  # Created in last 2 minutes
                        folder_violations.append(dir_path)
                        log_message(f"[PROTECTION] ❌ ROOT FOLDER VIOLATION: {dir_path}")
                        
                        # Auto-delete the folder
                        import shutil
                        try:
                            shutil.rmtree(dir_path)
                            log_message(f"[PROTECTION] ✅ Deleted root folder violation: {dir_path}")
                        except Exception as delete_error:
                            log_message(f"[PROTECTION] ⚠️ Failed to delete folder: {delete_error}")
                except Exception as e:
                    log_message(f"[PROTECTION] Error checking folder {dir_path}: {e}")
        
        if violations:
            log_message(f"[PROTECTION] ❌ ROOT VIOLATION: Files modified: {violations}")
            
            # REVERT from Git
            import subprocess
            revert_result = subprocess.run(
                ["git", "checkout", "HEAD", "--"] + violations,
                capture_output=True,
                text=True
            )
            
            if revert_result.returncode == 0:
                log_message(f"[PROTECTION] ✅ Reverted root file violations: {violations}")
                return {
                    "status": "violation",
                    "files_reverted": violations,
                    "folders_deleted": folder_violations if folder_violations else [],
                    "message": f"Root files were modified and have been automatically reverted: {', '.join(violations)}"
                }
            else:
                log_message(f"[PROTECTION] ⚠️ Failed to revert: {revert_result.stderr}")
        
        if folder_violations:
            return {
                "status": "violation",
                "folders_deleted": folder_violations,
                "message": f"Root folders were created and have been automatically deleted: {', '.join(folder_violations)}"
            }
        
        return {"status": "ok", "message": "No root file or folder violations detected"}
        
    except Exception as e:
        log_message(f"[PROTECTION] Error in post-execution validation: {e}")
        return {"status": "error", "message": str(e)}


# ===============================
# Thread-Safe JSON Operations
# ===============================

def read_json_safe(path: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Thread-safe JSON file reading with automatic error recovery.
    
    This is a convenience wrapper around core.memory_lock.safe_read_json.
    
    Args:
        path: Path to JSON file
        default: Default value to return if file doesn't exist or is corrupted
        
    Returns:
        dict: Parsed JSON data or default value
        
    Example:
        data = read_json_safe("projects/MyProject/.lazydeve/memory.json", {"status": "new"})
    """
    return safe_read_json(path, default)


def write_json_safe(path: str, data: Dict[str, Any], create_backup: bool = False) -> bool:
    """
    Thread-safe JSON file writing with optional backup.
    
    This is a convenience wrapper around core.memory_lock.safe_write_json.
    
    Args:
        path: Path to JSON file
        data: Dictionary to write
        create_backup: Whether to create backup before writing (default: False)
        
    Returns:
        bool: True if write succeeded, False otherwise
        
    Example:
        success = write_json_safe("projects/MyProject/.lazydeve/memory.json", memory_data, create_backup=True)
    """
    return safe_write_json(path, data, create_backup=create_backup)


def append_log_safe(path: str, message: str) -> bool:
    """
    Thread-safe log file appending with automatic timestamp.
    
    This is a convenience wrapper around core.memory_lock.safe_append_log.
    
    Args:
        path: Path to log file
        message: Message to append
        
    Returns:
        bool: True if append succeeded, False otherwise
        
    Example:
        append_log_safe("projects/MyProject/.lazydeve/logs/actions.log", "Project created")
    """
    return safe_append_log(path, message)


# ===============================
# Debug Entry
# ===============================

if __name__ == "__main__":
    init_environment()
    print("basic_functional.py ready.")
