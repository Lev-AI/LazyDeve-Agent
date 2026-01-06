"""
Git Routes - Git operations (commit, sync, status, history)
Extracted from agent.py for Task 7 Phase 2
"""

import subprocess
from typing import Optional
from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from datetime import datetime
from api.schemas import CommitRequest, FormatCommitRequest
from core.auth_middleware import verify_token
from core.basic_functional import log_message
from core.memory_utils import update_memory, log_project_action
from core.event_bus import trigger_event
from core.system_protection import get_active_project_context
from utils.git_utils import safe_git_pull, safe_git_add, safe_git_commit, safe_git_push, safe_git_command

router = APIRouter()


@router.post("/commit", dependencies=[Depends(verify_token)])
def commit_changes(body: CommitRequest):
    """
    Commit changes to the active project's Git repository.
    Accepts JSON: { "message": "your commit message", "project": "optional_name" }
    If 'project' is not provided, uses the active project from context.
    All Git operations are isolated to the specified project's repository.
    """
    try:
        message = body.message
        project = body.project
        
        # ✅ TASK 3.5: Detect active project context
        if not project:
            project_info = get_active_project_context()
            project = project_info.get("project")
        
        if not project:
            return JSONResponse(
                {"status": "error", "message": "No active project"},
                status_code=400
            )
        
        # Get project path for cwd parameter
        project_path = f"projects/{project}"
        
        log_message(f"[GitAPI] Committing to project: {project}")
        
        # ✅ TASK 4.2.3: Ensure GitHub remote exists before commit/push
        from utils.github_api import ensure_github_remote_exists
        from core.config import allow_github_access
        
        if allow_github_access:
            remote_result = ensure_github_remote_exists(project, project_path)
            if remote_result["status"] == "created":
                log_message(f"[GitAPI] ✅ GitHub repo auto-created for {project}")
            elif remote_result["status"] == "linked":
                log_message(f"[GitAPI] ✅ GitHub repo linked for {project}")
        
        # ✅ TASK 3.5: Git add with project context
        add_result = safe_git_add(cwd=project_path)
        if add_result["status"] != "success":
            return JSONResponse(
                {"status": "error", "message": "Failed to add files", "error": add_result.get("error", "")},
                status_code=500
            )

        # ✅ TASK 3.5: Git commit with project context
        commit_result = safe_git_commit(message, cwd=project_path)
        if commit_result["status"] != "success":
            return JSONResponse(
                {"status": "error", "message": "Failed to commit", "error": commit_result.get("error", "")},
                status_code=500
            )

        # ✅ TASK 3.5: Git push with project context
        push_result = safe_git_push(cwd=project_path)
        
        push_success = push_result["status"] == "success"
        
        # Memory Hooks Integration (Task 7.7.3b)
        if push_success:
            try:
                # Update project memory with commit action
                update_memory(project, "commit", f"Commit: {message[:50]}", 
                             extra={"push_success": push_success})
                
                # Log action to project log
                log_project_action(project, "commit", f"Changes committed: {message[:80]}")
                
            except Exception as memory_error:
                # Don't fail the request if memory update fails
                log_message(f"[Memory Hooks] Error updating memory for {project}: {memory_error}")
        
        # Trigger post-action event hooks
        trigger_event(
            "post_action",
            async_mode=True,
            project=project,
            action="commit",
            details=message[:100],  # Truncate for brevity
            success=push_success,
            commit_message=message
        )
        trigger_event("post_commit", async_mode=True, project=project, message=message, push_success=push_success)
        
        # ✅ TASK 8.8: Generate commit report
        try:
            from core.commit_tracker import generate_commit_report
            if project:
                commit_report = generate_commit_report(project)
                if commit_report:
                    log_message(f"[Git] ✅ Commit report generated: {commit_report['commit_id']}")
                    
                    # Update snapshot
                    from core.context_sync import update_snapshot
                    update_snapshot(project, {
                        "last_commit": commit_report['commit_id'],
                        "pending_changes": False
                    })
        except Exception as e:
            log_message(f"[Git] ⚠️ Commit report generation failed: {e}")
        
        return JSONResponse(
            {
                "status": "success",
                "project": project,
                "commit_message": message,
                "push_status": "success" if push_success else "failed",
                "output": push_result.get("stdout", "") or push_result.get("stderr", "")
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": "Failed to commit changes", "error": str(e)},
            status_code=500
        )


@router.post("/push", dependencies=[Depends(verify_token)])
def push_changes(project: Optional[str] = None, branch: str = "main"):
    """
    Push commits to remote repository for the active project.
    If 'project' is not provided, uses the active project from context.
    All Git operations are isolated to the specified project's repository.
    
    ⚠️ SAFETY: This endpoint does NOT affect auto-commit systems.
    Auto-commit systems use safe_git_push() directly, not this endpoint.
    
    Args:
        project: Project name (optional, uses active project from context)
        branch: Branch name to push (default: "main")
    
    Returns:
        Push operation result with status
    """
    try:
        # ✅ TASK 3.5: Detect active project context
        if not project:
            project_info = get_active_project_context()
            project = project_info.get("project")
        
        if not project:
            return JSONResponse(
                {"status": "error", "message": "No active project"},
                status_code=400
            )
        
        # Get project path for cwd parameter
        project_path = f"projects/{project}"
        
        log_message(f"[GitAPI] Pushing to remote for project: {project}")
        
        # ✅ Use safe_git_push utility (same as /commit endpoint)
        push_result = safe_git_push(branch=branch, cwd=project_path)
        
        push_success = push_result["status"] == "success"
        
        # Trigger post-action event hooks
        trigger_event(
            "post_action",
            async_mode=True,
            project=project,
            action="push",
            details=f"Push to {branch}",
            success=push_success
        )
        
        if push_success:
            return JSONResponse(
                {
                    "status": "success",
                    "project": project,
                    "branch": branch,
                    "message": "Changes pushed successfully",
                    "output": push_result.get("stdout", "") or push_result.get("stderr", "")
                },
                status_code=200
            )
        else:
            # Handle "no remote" gracefully (local-only repos)
            if "no remote" in push_result.get("error", "").lower():
                return JSONResponse(
                    {
                        "status": "info",
                        "project": project,
                        "branch": branch,
                        "message": "Local commit only (no remote configured)",
                        "output": push_result.get("stdout", "") or push_result.get("stderr", "")
                    },
                    status_code=200
                )
            else:
                return JSONResponse(
                    {
                        "status": "error",
                        "project": project,
                        "branch": branch,
                        "message": "Failed to push changes",
                        "error": push_result.get("error", "")
                    },
                    status_code=500
                )
        
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": "Failed to push changes", "error": str(e)},
            status_code=500
        )


@router.post("/format-commit")
def format_commit_endpoint(body: FormatCommitRequest):
    """
    Format commit message via JSON request.
    Accepts JSON: { "message": "your message", "commit_type": "optional_type" }
    """
    try:
        message = body.message
        commit_type = body.commit_type
        
        # Format the commit message
        if commit_type:
            formatted_message = f"[LazyDeve] {commit_type}: {message}"
        else:
            formatted_message = f"[LazyDeve] feat: {message}"
        
        return JSONResponse(
            {
                "status": "success",
                "original_message": message,
                "formatted_message": formatted_message,
                "commit_type": commit_type
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": "Failed to format commit message", "error": str(e)},
            status_code=500
        )


@router.post("/sync")
def sync_api(project: Optional[str] = None):
    """
    Sync the active project with remote repository (git pull).
    If 'project' is not provided, uses the active project from context.
    Returns pull result status for the project's isolated Git repository.
    """
    try:
        # ✅ TASK 3.5: Detect active project context
        if not project:
            project_info = get_active_project_context()
            project = project_info.get("project")
        
        if not project:
            return JSONResponse(
                {"status": "error", "message": "No active project"},
                status_code=400
            )
        
        # Get project path for cwd parameter
        project_path = f"projects/{project}"
        
        log_message(f"[GitAPI] Syncing project: {project}")
        
        # ✅ TASK 4.2.3: Ensure GitHub remote exists before sync
        from utils.github_api import ensure_github_remote_exists
        from core.config import allow_github_access
        
        if allow_github_access:
            remote_result = ensure_github_remote_exists(project, project_path)
            if remote_result["status"] == "created":
                log_message(f"[GitAPI] ✅ GitHub repo auto-created for {project} before sync")
            elif remote_result["status"] == "linked":
                log_message(f"[GitAPI] ✅ GitHub repo linked for {project} before sync")
        
        # ✅ TASK 3.5: Git pull with project context
        result = safe_git_pull(cwd=project_path)
        return {
            "status": result["status"],
            "project": project,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "message": result["message"],
            "error": result.get("error", "")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/pull", dependencies=[Depends(verify_token)])
def pull_changes(project: Optional[str] = None):
    """
    Pull changes from remote repository for the active project.
    If 'project' is not provided, uses the active project from context.
    All Git operations are isolated to the specified project's repository.
    
    ⚠️ SAFETY: This endpoint does NOT affect auto-commit systems.
    Auto-commit systems use safe_git_pull() directly, not this endpoint.
    
    Args:
        project: Project name (optional, uses active project from context)
    
    Returns:
        Pull operation result with status
    """
    try:
        # ✅ TASK 3.5: Detect active project context
        if not project:
            project_info = get_active_project_context()
            project = project_info.get("project")
        
        if not project:
            return JSONResponse(
                {"status": "error", "message": "No active project"},
                status_code=400
            )
        
        # Get project path for cwd parameter
        project_path = f"projects/{project}"
        
        log_message(f"[GitAPI] Pulling from remote for project: {project}")
        
        # ✅ Use safe_git_pull utility (same as /sync endpoint)
        pull_result = safe_git_pull(cwd=project_path)
        
        # Trigger post-action event hooks
        trigger_event(
            "post_action",
            async_mode=True,
            project=project,
            action="pull",
            details="Pull from remote",
            success=pull_result["status"] == "success"
        )
        
        return JSONResponse(
            {
                "status": pull_result["status"],
                "project": project,
                "stdout": pull_result.get("stdout", ""),
                "stderr": pull_result.get("stderr", ""),
                "message": pull_result.get("message", ""),
                "error": pull_result.get("error", "")
            },
            status_code=200 if pull_result["status"] == "success" else 500
        )
        
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": "Failed to pull changes", "error": str(e)},
            status_code=500
        )


@router.get("/diff", dependencies=[Depends(verify_token)])
def get_diff(project: Optional[str] = None, file_path: Optional[str] = None):
    """
    Show file changes (diff) for the active project.
    If 'project' is not provided, uses the active project from context.
    If 'file_path' is provided, shows diff for specific file only.
    
    Args:
        project: Project name (optional, uses active project from context)
        file_path: Specific file path to diff (optional, shows all changes if not provided)
    
    Returns:
        Diff output with status
    """
    try:
        # ✅ TASK 3.5: Detect active project context
        if not project:
            project_info = get_active_project_context()
            project = project_info.get("project")
        
        if not project:
            return JSONResponse(
                {"status": "error", "message": "No active project"},
                status_code=400
            )
        
        # Get project path for cwd parameter
        project_path = f"projects/{project}"
        
        log_message(f"[GitAPI] Getting diff for project: {project}")
        
        # Build git diff command
        if file_path:
            # Diff specific file
            diff_args = ["git", "diff", file_path]
        else:
            # Diff all changes
            diff_args = ["git", "diff"]
        
        # Execute git diff with project context
        diff_result = safe_git_command(diff_args, timeout=15, cwd=project_path)
        
        if diff_result["status"] == "success":
            diff_output = diff_result.get("stdout", "")
            
            # If no changes, return empty diff
            if not diff_output.strip():
                return JSONResponse(
                    {
                        "status": "success",
                        "project": project,
                        "file_path": file_path,
                        "diff": "",
                        "message": "No changes detected"
                    },
                    status_code=200
                )
            
            return JSONResponse(
                {
                    "status": "success",
                    "project": project,
                    "file_path": file_path,
                    "diff": diff_output,
                    "message": "Diff retrieved successfully"
                },
                status_code=200
            )
        else:
            return JSONResponse(
                {
                    "status": "error",
                    "project": project,
                    "file_path": file_path,
                    "message": "Failed to get diff",
                    "error": diff_result.get("error", "")
                },
                status_code=500
            )
        
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": "Failed to get diff", "error": str(e)},
            status_code=500
        )


@router.get("/status")
def get_status(project: Optional[str] = None):
    """
    Get real-time Git information for the active project including commit hash, message, date, and branch.
    If 'project' is not provided, uses the active project from context.
    Returns agent freshness and synchronization state for the project's isolated Git repository.
    """
    try:
        # ✅ TASK 3.5: Detect active project context
        if not project:
            project_info = get_active_project_context()
            project = project_info.get("project")
        
        if not project:
            return JSONResponse(
                {"status": "error", "message": "No active project"},
                status_code=400
            )
        
        # Get project path for cwd parameter
        project_path = f"projects/{project}"
        
        # ✅ TASK 3.5: Get current branch name with project context
        branch_output = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path,
            stderr=subprocess.STDOUT,
            timeout=10
        ).decode("utf-8").strip()
        
        # ✅ TASK 3.5: Get last commit hash with project context
        commit_hash_output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_path,
            stderr=subprocess.STDOUT,
            timeout=10
        ).decode("utf-8").strip()
        
        # ✅ TASK 3.5: Get last commit message and date with project context
        commit_info_output = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%s|%ci"],
            cwd=project_path,
            stderr=subprocess.STDOUT,
            timeout=10
        ).decode("utf-8").strip()
        
        # Parse commit message and date
        if "|" in commit_info_output:
            commit_message, commit_date = commit_info_output.split("|", 1)
        else:
            commit_message = commit_info_output
            commit_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
        
        # Return success response
        return JSONResponse({
            "status": "ok",
            "project": project,
            "branch": branch_output,
            "last_commit": commit_hash_output[:7],  # Short hash
            "message": commit_message,
            "date": commit_date,
            "timestamp": datetime.now().isoformat()
        }, status_code=200)
        
    except subprocess.CalledProcessError as e:
        error_msg = e.output.decode("utf-8") if e.output else str(e)
        log_message(f"[Status Endpoint] Git command failed: {error_msg}")
        return JSONResponse({
            "status": "error",
            "message": f"Git command failed: {error_msg}",
            "timestamp": datetime.now().isoformat()
        }, status_code=500)
        
    except subprocess.TimeoutExpired:
        log_message("[Status Endpoint] Git command timeout")
        return JSONResponse({
            "status": "error",
            "message": "Git command timeout",
            "timestamp": datetime.now().isoformat()
        }, status_code=504)
        
    except Exception as e:
        log_message(f"[Status Endpoint] Unexpected error: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, status_code=500)


@router.get("/commits")
def get_commits(limit: int = 5, project: Optional[str] = None):
    """
    Get recent Git commit history for the active project with optional limit parameter.
    If 'project' is not provided, uses the active project from context.
    Returns commit hash, message, and date from the project's isolated Git repository.
    """
    try:
        # Validate limit parameter
        if limit < 1 or limit > 50:
            return JSONResponse({
                "status": "error",
                "message": "Limit must be between 1 and 50",
                "timestamp": datetime.now().isoformat()
            }, status_code=400)
        
        # ✅ TASK 3.5: Detect active project context
        if not project:
            project_info = get_active_project_context()
            project = project_info.get("project")
        
        if not project:
            return JSONResponse(
                {"status": "error", "message": "No active project"},
                status_code=400
            )
        
        # Get project path for cwd parameter
        project_path = f"projects/{project}"
        
        # ✅ TASK 3.5: Get recent commits with project context
        output = subprocess.check_output(
            ["git", "log", f"-{limit}", "--pretty=format:%h - %s (%ci)"],
            cwd=project_path,
            stderr=subprocess.STDOUT,
            timeout=15
        ).decode("utf-8").splitlines()
        
        # Filter out empty lines
        commits = [line.strip() for line in output if line.strip()]
        
        log_message(f"[Commits Endpoint] Retrieved {len(commits)} commits for project {project} (limit: {limit})")
        
        return JSONResponse({
            "status": "success",
            "project": project,
            "commits": commits,
            "count": len(commits),
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }, status_code=200)
        
    except subprocess.CalledProcessError as e:
        error_msg = e.output.decode("utf-8") if e.output else str(e)
        log_message(f"[Commits Endpoint] Git command failed: {error_msg}")
        return JSONResponse({
            "status": "error",
            "message": f"Git command failed: {error_msg}",
            "timestamp": datetime.now().isoformat()
        }, status_code=500)
        
    except subprocess.TimeoutExpired:
        log_message("[Commits Endpoint] Git command timeout")
        return JSONResponse({
            "status": "error",
            "message": "Git command timeout",
            "timestamp": datetime.now().isoformat()
        }, status_code=504)
        
    except Exception as e:
        log_message(f"[Commits Endpoint] Unexpected error: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, status_code=500)


@router.post("/rename-project")
def rename(src: str = Body(...), dst: str = Body(...)):
    """
    Rename a project directory.
    """
    from core.custom_functional import rename_project
    return rename_project(src, dst)

