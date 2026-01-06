"""
Git Utilities - Safe Git operations with error handling
Extracted from agent.py for better modularity.
"""

import subprocess
import os
import shutil
from core.basic_functional import log_message


def safe_git_command(args, message=None, timeout=30, cwd=None):
    """
    Safe wrapper for Git operations with error handling and commit message translation.
    
    Args:
        args: List of Git command arguments (e.g., ["git", "add", "-A"])
        message: Optional commit message (will be translated to English)
        timeout: Timeout in seconds (default: 30)
        cwd: Working directory for Git command (defaults to current directory)
    
    Returns:
        dict: {"status": "success/error", "message": "...", "error": "...", "cwd": "..."}
    """
    try:
        # Import translation here to avoid circular imports
        from utils.translation import gpt_translate_to_english
        
        # Translate commit message if provided and not English
        if message:
            translated_message = gpt_translate_to_english(message)
            if translated_message != message:
                log_message(f"[Git] Commit message translated: '{message}' → '{translated_message}'")
            message = translated_message
        
        # Log execution context
        cwd_display = cwd if cwd else "current directory"
        log_message(f"[GitUtils] Executing in {cwd_display}: {' '.join(args)}")
        
        # Execute Git command with proper error handling and cwd parameter
        result = subprocess.run(
            args, 
            check=True, 
            text=True, 
            encoding="utf-8",
            capture_output=True,
            timeout=timeout,
            cwd=cwd  # <-- Execute in specified directory
        )
        
        success_msg = f"✅ Git command executed successfully: {' '.join(args)}"
        log_message(f"[Git] {success_msg}")
        return {
            "status": "success",
            "message": success_msg,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": cwd
        }
        
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ Git command failed: {' '.join(args)} - {e}"
        log_message(f"[Git] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "error": e.stderr if hasattr(e, 'stderr') else str(e),
            "returncode": e.returncode,
            "cwd": cwd
        }
    except subprocess.TimeoutExpired as e:
        error_msg = f"❌ Git command timed out after {timeout}s: {' '.join(args)}"
        log_message(f"[Git] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "error": "Command timed out",
            "cwd": cwd
        }
    except Exception as e:
        error_msg = f"❌ Git command error: {' '.join(args)} - {e}"
        log_message(f"[Git] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "cwd": cwd
        }


def safe_git_add(files=None, cwd=None):
    """
    Safe Git add operation.
    
    Args:
        files: List of files to add (None for all files)
        cwd: Working directory (defaults to current directory)
    """
    if files is None:
        args = ["git", "add", "-A"]
    else:
        args = ["git", "add"] + files
    return safe_git_command(args, timeout=10, cwd=cwd)


def safe_git_commit(message, timeout=15, cwd=None):
    """
    Safe Git commit operation with message translation.
    
    Args:
        message: Commit message (will be translated to English)
        timeout: Timeout in seconds (default: 15)
        cwd: Working directory (defaults to current directory)
    """
    from utils.translation import gpt_translate_to_english
    
    # Translate the message first
    translated_message = gpt_translate_to_english(message)
    if translated_message != message:
        log_message(f"[Git] Commit message translated: '{message}' → '{translated_message}'")
    
    args = ["git", "commit", "-m", translated_message]
    return safe_git_command(args, timeout=timeout, cwd=cwd)


def safe_git_push(branch="main", timeout=30, cwd=None):
    """
    Safe Git push operation.
    
    Args:
        branch: Branch name to push (default: "main")
        timeout: Timeout in seconds (default: 30)
        cwd: Working directory (defaults to current directory)
    """
    args = ["git", "push", "origin", branch]
    return safe_git_command(args, timeout=timeout, cwd=cwd)


def safe_git_pull(timeout=30, cwd=None):
    """
    Safe Git pull operation.
    
    Args:
        timeout: Timeout in seconds (default: 30)
        cwd: Working directory (defaults to current directory)
    """
    args = ["git", "pull"]
    return safe_git_command(args, timeout=timeout, cwd=cwd)


def safe_git_status(timeout=10, cwd=None):
    """
    Safe Git status operation.
    
    Args:
        timeout: Timeout in seconds (default: 10)
        cwd: Working directory (defaults to current directory)
    """
    args = ["git", "status", "--porcelain"]
    return safe_git_command(args, timeout=timeout, cwd=cwd)


def safe_git_rm(path, timeout=15, cwd=None):
    """
    Safe Git remove operation.
    
    Args:
        path: Path to remove from Git index
        timeout: Timeout in seconds (default: 15)
        cwd: Working directory (defaults to current directory)
    """
    args = ["git", "rm", "-r", "--cached", "--ignore-unmatch", path]
    return safe_git_command(args, timeout=timeout, cwd=cwd)


def remove_via_git(path: str, cwd=None):
    """
    Enhanced deletion with local cleanup and post-push sync.
    Addresses sync reliability issues and nested folder handling.
    
    Args:
        path: Path to delete
        cwd: Working directory for Git operations (defaults to current directory)
    """
    try:
        from utils.path_utils import is_restricted_path
        
        cwd_display = cwd if cwd else "current directory"
        log_message(f"[Agent] 🗑️ Starting enhanced Git-driven deletion for: {path} (cwd: {cwd_display})")
        
        # ==============================
        # Safety & validation checks
        # ==============================
        
        # Check for invalid or empty paths
        if not path or len(path) < 2 or path.lower() in ["the", "file", "folder", "a", "an"]:
            error_msg = f"Invalid or empty deletion target: {path}"
            log_message(f"[Agent] ❌ {error_msg}")
            return {"status": "error", "message": error_msg, "path": path}
        
        # Prevent potentially dangerous paths (directory traversal, absolute paths, drive letters)
        if ".." in path or path.startswith("/") or path.startswith("\\") or ":" in path:
            error_msg = f"Unsafe deletion path blocked: {path}"
            log_message(f"[Security] 🚫 {error_msg}")
            return {"status": "error", "message": error_msg, "path": path}
        
        # Check if path is in restricted directories
        if is_restricted_path(path):
            error_msg = f"Deletion blocked: {path} is a protected directory"
            log_message(f"[Protection] 🚫 {error_msg}")
            return {"status": "error", "message": error_msg, "path": path}
        
        # ✅ BUG FIX (Task 8.8.2 Bug #3): Prevent accidental project folder deletion
        # Defense in depth: Even if path injection fails, this prevents project deletion
        # Check if path is a project root directory
        if path.startswith("projects/") and os.path.isdir(path):
            # Extract project name
            parts = path.replace("\\", "/").split("/")
            if len(parts) == 2 and parts[0] == "projects":
                project_name = parts[1]
                # Check if this is a project root (has .lazydeve or .git)
                project_root = os.path.join("projects", project_name)
                if os.path.exists(os.path.join(project_root, ".lazydeve")) or \
                   os.path.exists(os.path.join(project_root, ".git")):
                    error_msg = f"Deletion blocked: Cannot delete project root '{project_name}'. Use /projects/archive/{project_name} instead."
                    log_message(f"[SECURITY] 🚫 {error_msg}")
                    return {"status": "error", "message": error_msg, "path": path}
        
        # ✅ BUG FIX (Task 8.8.4): Prevent cross-project deletion (defense in depth)
        # Validate path belongs to active project
        if path.startswith("projects/"):
            from core.context_manager import context_manager
            active_project = context_manager.get_project()
            if active_project:
                parts = path.replace("\\", "/").split("/")
                if len(parts) >= 2 and parts[0] == "projects":
                    path_project = parts[1]
                    if path_project != active_project:
                        error_msg = f"Deletion blocked: Path '{path}' belongs to project '{path_project}', but active project is '{active_project}'. Cross-project operations are not allowed."
                        log_message(f"[SECURITY] 🚫 {error_msg}")
                        return {"status": "error", "message": error_msg, "path": path, "error_code": "PATH_OUTSIDE_PROJECT"}
        
        # Verify local file exists before proceeding
        if not os.path.exists(path):
            warning_msg = f"File not found locally: {path}"
            log_message(f"[Agent] ⚠️ {warning_msg}")
            return {"status": "warning", "message": warning_msg, "path": path}
        
        # 1. Local filesystem cleanup first (addresses Issue 1: Local state lag)
        local_cleaned = False
        if os.path.exists(path):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    log_message(f"[Agent] 🗑️ Local file {path} removed before Git cleanup")
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    log_message(f"[Agent] 🗑️ Local directory {path} removed before Git cleanup")
                local_cleaned = True
            except Exception as cleanup_error:
                log_message(f"[Agent] ⚠️ Local cleanup warning for {path}: {cleanup_error}")
        
        # 2. Stage all changes (including deletions)
        add_result = safe_git_add(cwd=cwd)
        if add_result["status"] != "success":
            return {"status": "error", "message": f"Git add failed: {add_result['error']}", "path": path}
        log_message(f"[Agent] 🗑️ All changes staged for: {path}")
        
        # 3. Remove from Git index (addresses Issue 2: Nested folder handling)
        rm_result = safe_git_rm(path, cwd=cwd)
        if rm_result["status"] != "success":
            # This is often expected for ignored/recreated folders - log as warning, not error
            log_message(f"[Agent] ⚠️ Git rm warning for {path}: {rm_result['error']} (may be already deleted or ignored)")
        else:
            log_message(f"[Agent] 🗑️ Git rm completed for: {path}")
        
        # 4. Commit the deletion with enhanced message
        commit_msg = f"chore: remove {path} and resync"
        commit_result = safe_git_commit(commit_msg, cwd=cwd)
        if commit_result["status"] != "success":
            return {"status": "error", "message": f"Git commit failed: {commit_result['error']}", "path": path}
        log_message(f"[Agent] 🗑️ Deletion committed: {commit_msg}")
        
        # 5. Push to GitHub (only if GitHub access is enabled)
        from core.config import allow_github_access
        
        push_result = None
        push_actually_succeeded = False
        
        if allow_github_access:
            # ✅ CRITICAL FIX: Ensure GitHub remote exists (same as update_file)
            # Extract project name and path from cwd or path
            project_path = cwd
            project_name = None
            
            if cwd:
                # ✅ CRITICAL FIX: Normalize path (Windows backslashes → forward slashes)
                normalized_cwd = cwd.replace("\\", "/")
                if "projects/" in normalized_cwd:
                    # Extract project name from cwd (e.g., "projects/MyProject" -> "MyProject")
                    project_name = os.path.basename(normalized_cwd)
                    project_path = normalized_cwd
            elif path:
                # ✅ CRITICAL FIX: Normalize path (Windows backslashes → forward slashes)
                normalized_path = path.replace("\\", "/")
                if "projects/" in normalized_path:
                    # Extract from path as fallback
                    import re
                    project_match = re.search(r'projects/([^/]+)', normalized_path)
                    if project_match:
                        project_name = project_match.group(1)
                        project_path = f"projects/{project_name}"
            
            if project_name and project_path:
                from utils.github_api import ensure_github_remote_exists
                remote_result = ensure_github_remote_exists(project_name, project_path)
                if remote_result["status"] == "created":
                    log_message(f"[Agent] ✅ GitHub repo auto-created and linked: {remote_result.get('repo_url', '')}")
                elif remote_result["status"] == "linked":
                    log_message(f"[Agent] ✅ Linked existing GitHub repo: {remote_result.get('repo_url', '')}")
                elif remote_result["status"] == "error":
                    log_message(f"[Agent] ⚠️ Auto-GitHub creation failed: {remote_result.get('error', '')}")
            
            log_message(f"[Agent] 🔄 Attempting to push deletion to GitHub: {path}")
            push_result = safe_git_push(branch="main", cwd=cwd)  # ✅ FIX: Explicit branch like update_file()
            
            # ✅ ENHANCED: Detailed logging for debugging
            log_message(f"[Agent] 🔍 Push result: status={push_result.get('status')}, stdout={push_result.get('stdout', '')[:100]}, error={push_result.get('error', 'N/A')}")
            
            if push_result["status"] == "success":
                log_message(f"[Agent] 🗑️ Deletion pushed to GitHub: {path}")
                push_actually_succeeded = True
            elif "no remote" in push_result.get("error", "").lower() or \
                 "does not match any" in push_result.get("error", "").lower():
                # ✅ TASK 3.6.2 FIX: Handle local-only repos gracefully
                log_message(f"[Agent] ⚠️ Local commit successful (no remote configured): {path}")
                push_result = {"status": "skipped", "error": "no remote configured"}
            else:
                # ✅ CRITICAL FIX: Don't fail deletion if push fails - commit succeeded!
                log_message(f"[Agent] ⚠️ Git push failed but commit succeeded: {push_result.get('error', 'Unknown error')}")
                push_result = {"status": "error", "error": push_result.get("error", "Unknown push error")}
                # Continue - deletion operation succeeded (file deleted and committed)
        else:
            # ✅ BUG FIX: GitHub access disabled - local commit only
            log_message(f"[Agent] ⚠️ Local commit successful (GitHub access disabled): {path}")
            push_result = {"status": "skipped", "error": "GitHub access disabled"}
        
        # 6. Force sync confirmation (only if push actually succeeded)
        pull_result = None
        if push_actually_succeeded:
            pull_result = safe_git_pull(cwd=cwd)
            if pull_result["status"] != "success":
                log_message(f"[Agent] ⚠️ Git pull warning: {pull_result['error']}")
            else:
                log_message(f"[Agent] ✅ Post-deletion sync confirmed: {path}")
            success_msg = f"✅ Enhanced deletion completed: {path} removed and synced with GitHub"
        else:
            # Local-only commit (no remote, GitHub disabled, or push failed)
            if push_result and push_result.get("status") == "skipped":
                reason = push_result.get("error", "unknown reason")
                success_msg = f"✅ Enhanced deletion completed: {path} removed and committed locally ({reason})"
            elif push_result and push_result.get("status") == "error":
                success_msg = f"✅ Enhanced deletion completed: {path} removed and committed locally (push failed: {push_result.get('error', 'unknown')})"
            else:
                success_msg = f"✅ Enhanced deletion completed: {path} removed and committed locally"
        
        log_message(f"[Agent] {success_msg}")
        print(success_msg)
        
        return {
            "status": "success", 
            "message": success_msg, 
            "path": path,
            "local_cleaned": local_cleaned,
            "sync_confirmed": pull_result["status"] == "success" if pull_result else False
        }
        
    except Exception as e:
        error_msg = f"❌ Enhanced deletion error for {path}: {e}"
        print(error_msg)
        log_message(f"[Agent] {error_msg}")
        return {"status": "error", "message": error_msg, "path": path}


def remove_via_git_multi(paths: list, cwd=None) -> dict:
    """
    🚀 Enhanced multi-file deletion routine.
    Handles multiple files in a single operation with comprehensive validation.
    Uses existing safe Git wrappers and supports full Unicode.
    
    Args:
        paths: List of file/folder paths to delete
        cwd: Working directory for Git operations (defaults to current directory)
    
    Returns:
        dict with status, deleted, skipped, and failed lists
    """
    if not paths:
        return {"status": "error", "message": "No paths provided", "deleted": [], "skipped": [], "failed": []}
    
    from utils.path_utils import is_restricted_path
    
    cwd_display = cwd if cwd else "current directory"
    log_message(f"[Agent] 🗑️ Starting multi-file deletion for {len(paths)} path(s) (cwd: {cwd_display})")
    
    deleted_paths = []
    skipped_paths = []
    failed_paths = []
    
    for path in paths:
        try:
            # Safety validation (same as single file)
            if not path or len(path) < 2:
                skipped_paths.append({"path": path, "reason": "Invalid path (too short)"})
                log_message(f"[Agent] ⚠️ Skipped (invalid): {path}")
                continue
            
            if path.lower() in ["the", "file", "folder", "files", "folders", "a", "an"]:
                skipped_paths.append({"path": path, "reason": "Filler word"})
                log_message(f"[Agent] ⚠️ Skipped (filler word): {path}")
                continue
            
            # Prevent dangerous paths
            if ".." in path or path.startswith("/") or path.startswith("\\") or ":" in path:
                skipped_paths.append({"path": path, "reason": "Unsafe path blocked"})
                log_message(f"[Security] 🚫 Skipped (unsafe): {path}")
                continue
            
            # Check if path is in restricted directories
            if is_restricted_path(path):
                skipped_paths.append({"path": path, "reason": "Protected directory"})
                log_message(f"[Protection] 🚫 Skipped (protected): {path}")
                continue
            
            # ✅ BUG FIX (Task 8.8.2 Bug #3): Prevent accidental project folder deletion (multi-file)
            # Defense in depth: Check if path is a project root directory
            if path.startswith("projects/") and os.path.isdir(path):
                parts = path.replace("\\", "/").split("/")
                if len(parts) == 2 and parts[0] == "projects":
                    project_name = parts[1]
                    project_root = os.path.join("projects", project_name)
                    if os.path.exists(os.path.join(project_root, ".lazydeve")) or \
                       os.path.exists(os.path.join(project_root, ".git")):
                        skipped_paths.append({"path": path, "reason": f"Cannot delete project root '{project_name}'. Use /projects/archive/{project_name} instead."})
                        log_message(f"[SECURITY] 🚫 Skipped (project root): {path}")
                        continue
            
            # ✅ BUG FIX (Task 8.8.4): Prevent cross-project deletion (multi-file, defense in depth)
            # Validate path belongs to active project
            if path.startswith("projects/"):
                from core.context_manager import context_manager
                active_project = context_manager.get_project()
                if active_project:
                    parts = path.replace("\\", "/").split("/")
                    if len(parts) >= 2 and parts[0] == "projects":
                        path_project = parts[1]
                        if path_project != active_project:
                            skipped_paths.append({"path": path, "reason": f"Path belongs to project '{path_project}', but active project is '{active_project}'. Cross-project operations are not allowed."})
                            log_message(f"[SECURITY] 🚫 Skipped (cross-project): {path}")
                            continue
            
            # Check if file exists
            if not os.path.exists(path):
                skipped_paths.append({"path": path, "reason": "File not found"})
                log_message(f"[Agent] ⚠️ Skipped (not found): {path}")
                continue
            
            # Local cleanup
            if os.path.isdir(path):
                shutil.rmtree(path)  # Removes directory and all contents
                log_message(f"[Agent] 🗑️ Local directory {path} removed")
            else:
                os.remove(path)
                log_message(f"[Agent] 🗑️ Local file {path} removed")
            
            deleted_paths.append(path)
            
        except Exception as e:
            failed_paths.append({"path": path, "error": str(e)})
            log_message(f"[Agent] ❌ Error deleting {path}: {e}")
    
    # If any files were deleted, commit and push
    if deleted_paths:
        try:
            log_message(f"[Agent] 🔄 Committing deletion of {len(deleted_paths)} file(s)")
            
            # Use existing safe Git wrappers with cwd parameter
            add_result = safe_git_add(cwd=cwd)
            if add_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Git add failed: {add_result['error']}",
                    "deleted": deleted_paths,
                    "skipped": skipped_paths,
                    "failed": failed_paths
                }
            
            # Commit with translated message
            files_list = ", ".join(deleted_paths[:3])  # Show first 3 files
            if len(deleted_paths) > 3:
                files_list += f" and {len(deleted_paths) - 3} more"
            commit_msg = f"chore: remove {files_list} and resync"
            
            commit_result = safe_git_commit(commit_msg, cwd=cwd)
            if commit_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Git commit failed: {commit_result['error']}",
                    "deleted": deleted_paths,
                    "skipped": skipped_paths,
                    "failed": failed_paths
                }
            
            # Push to remote (only if GitHub access is enabled)
            from core.config import allow_github_access
            
            push_result = None
            push_actually_succeeded = False
            
            if allow_github_access:
                # ✅ CRITICAL FIX: Ensure GitHub remote exists (same as update_file)
                # Extract project name and path from cwd or first deleted path
                project_path = cwd
                project_name = None
                
                if cwd:
                    # ✅ CRITICAL FIX: Normalize path (Windows backslashes → forward slashes)
                    normalized_cwd = cwd.replace("\\", "/")
                    if "projects/" in normalized_cwd:
                        # Extract project name from cwd (e.g., "projects/MyProject" -> "MyProject")
                        project_name = os.path.basename(normalized_cwd)
                        project_path = normalized_cwd
                elif deleted_paths and len(deleted_paths) > 0:
                    # ✅ CRITICAL FIX: Normalize path (Windows backslashes → forward slashes)
                    normalized_first_path = deleted_paths[0].replace("\\", "/")
                    # Extract from first deleted path as fallback
                    import re
                    project_match = re.search(r'projects/([^/]+)', normalized_first_path)
                    if project_match:
                        project_name = project_match.group(1)
                        project_path = f"projects/{project_name}"
                
                if project_name and project_path:
                    from utils.github_api import ensure_github_remote_exists
                    remote_result = ensure_github_remote_exists(project_name, project_path)
                    if remote_result["status"] == "created":
                        log_message(f"[Agent] ✅ GitHub repo auto-created and linked: {remote_result.get('repo_url', '')}")
                    elif remote_result["status"] == "linked":
                        log_message(f"[Agent] ✅ Linked existing GitHub repo: {remote_result.get('repo_url', '')}")
                    elif remote_result["status"] == "error":
                        log_message(f"[Agent] ⚠️ Auto-GitHub creation failed: {remote_result.get('error', '')}")
                
                log_message(f"[Agent] 🔄 Attempting to push multi-file deletion to GitHub: {len(deleted_paths)} file(s)")
                push_result = safe_git_push(branch="main", cwd=cwd)  # ✅ FIX: Explicit branch like update_file()
                
                # ✅ ENHANCED: Detailed logging for debugging
                log_message(f"[Agent] 🔍 Push result: status={push_result.get('status')}, stdout={push_result.get('stdout', '')[:100]}, error={push_result.get('error', 'N/A')}")
                
                if push_result["status"] == "success":
                    log_message(f"[Agent] 🗑️ Multi-file deletion pushed to GitHub")
                    push_actually_succeeded = True
                elif "no remote" in push_result.get("error", "").lower() or \
                     "does not match any" in push_result.get("error", "").lower():
                    # ✅ TASK 3.6.2 FIX: Handle local-only repos gracefully
                    log_message(f"[Agent] ⚠️ Local commit successful (no remote configured) for {len(deleted_paths)} file(s)")
                    push_result = {"status": "skipped", "error": "no remote configured"}
                else:
                    # ✅ CRITICAL FIX: Don't fail deletion if push fails - commit succeeded!
                    log_message(f"[Agent] ⚠️ Git push failed but commit succeeded: {push_result.get('error', 'Unknown error')}")
                    push_result = {"status": "error", "error": push_result.get("error", "Unknown push error")}
                    # Continue - deletion operation succeeded (files deleted and committed)
            else:
                # ✅ BUG FIX: GitHub access disabled - local commit only
                log_message(f"[Agent] ⚠️ Local commit successful (GitHub access disabled) for {len(deleted_paths)} file(s)")
                push_result = {"status": "skipped", "error": "GitHub access disabled"}
            
            # Force sync confirmation (only if push actually succeeded)
            pull_result = None
            if push_actually_succeeded:
                pull_result = safe_git_pull(cwd=cwd)
                if pull_result["status"] != "success":
                    log_message(f"[Agent] ⚠️ Git pull warning: {pull_result['error']}")
                else:
                    log_message(f"[Agent] ✅ Post-deletion sync confirmed for {len(deleted_paths)} file(s)")
            
            # Build success message based on actual push status
            if push_actually_succeeded:
                success_msg = f"✅ Multi-file deletion completed: {len(deleted_paths)} deleted, {len(skipped_paths)} skipped, {len(failed_paths)} failed (synced with GitHub)"
            elif push_result and push_result.get("status") == "skipped":
                reason = push_result.get("error", "unknown reason")
                success_msg = f"✅ Multi-file deletion completed: {len(deleted_paths)} deleted, {len(skipped_paths)} skipped, {len(failed_paths)} failed (committed locally: {reason})"
            elif push_result and push_result.get("status") == "error":
                success_msg = f"✅ Multi-file deletion completed: {len(deleted_paths)} deleted, {len(skipped_paths)} skipped, {len(failed_paths)} failed (committed locally, push failed: {push_result.get('error', 'unknown')})"
            else:
                success_msg = f"✅ Multi-file deletion completed: {len(deleted_paths)} deleted, {len(skipped_paths)} skipped, {len(failed_paths)} failed"
            log_message(f"[Agent] {success_msg}")
            print(success_msg)
            
            return {
                "status": "success",
                "message": success_msg,
                "deleted": deleted_paths,
                "skipped": skipped_paths,
                "failed": failed_paths,
                "sync_confirmed": pull_result["status"] == "success" if pull_result else False
            }
            
        except Exception as e:
            error_msg = f"Git operations failed: {e}"
            log_message(f"[Agent] ❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "deleted": deleted_paths,
                "skipped": skipped_paths,
                "failed": failed_paths
            }
    else:
        warning_msg = f"No files deleted: {len(skipped_paths)} skipped, {len(failed_paths)} failed"
        log_message(f"[Agent] ⚠️ {warning_msg}")
        return {
            "status": "warning",
            "message": warning_msg,
            "deleted": [],
            "skipped": skipped_paths,
            "failed": failed_paths
        }

