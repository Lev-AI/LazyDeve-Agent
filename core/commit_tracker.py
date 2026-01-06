"""
Commit Tracker - Structured commit metadata generation
✅ TASK 8.8: Commit report generation
✅ TASK 8.10.1: Unified commit_history.json (merged from commit_report.json + commit_history.jsonl)
"""

import os
import json
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from core.basic_functional import log_message
from core.memory_lock import safe_write_json, safe_read_json


def get_max_commits_config(project_name: str) -> int:
    """
    Get max_commits configuration from config.json (default: 3).
    ✅ TASK 8.10.1: Configurable commit history limit
    
    Args:
        project_name: Project name
        
    Returns:
        int: Maximum number of commits to keep in history
    """
    config_path = f"projects/{project_name}/.lazydeve/config.json"
    if os.path.exists(config_path):
        try:
            config = safe_read_json(config_path, {})
            commit_config = config.get("commit_history", {})
            max_commits = commit_config.get("max_commits", 3)
            return max(1, int(max_commits))  # Ensure at least 1
        except Exception:
            pass
    
    return 3  # Default: 3 commits


def migrate_to_unified_commit_history(project_name: str) -> bool:
    """
    Migrate from old format (commit_report.json + commit_history.jsonl) to unified commit_history.json.
    ✅ TASK 8.10.1: Auto-migration for backward compatibility
    
    Args:
        project_name: Project name
        
    Returns:
        bool: True if migration successful or not needed
    """
    try:
        unified_path = f"projects/{project_name}/.lazydeve/commit_history.json"
        
        # If unified file already exists, migration not needed
        if os.path.exists(unified_path):
            return True
        
        log_message(f"[CommitTracker] 🔄 Migrating commit history to unified format for {project_name}")
        
        # Read old files
        old_report_path = f"projects/{project_name}/.lazydeve/commit_report.json"
        old_history_path = f"projects/{project_name}/.lazydeve/commit_history.jsonl"
        
        last_commit = None
        history = []
        
        # Load commit_report.json (if exists)
        if os.path.exists(old_report_path):
            try:
                last_commit = safe_read_json(old_report_path, None)
            except Exception as e:
                log_message(f"[CommitTracker] ⚠️ Could not read old commit_report.json: {e}")
        
        # Load commit_history.jsonl (if exists)
        if os.path.exists(old_history_path):
            try:
                with open(old_history_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                commit = json.loads(line)
                                history.append(commit)
                            except json.JSONDecodeError:
                                continue
                # Reverse to get most recent first
                history = list(reversed(history))
            except Exception as e:
                log_message(f"[CommitTracker] ⚠️ Could not read old commit_history.jsonl: {e}")
        
        # If we have last_commit but it's not in history, add it
        if last_commit and history:
            # Check if last_commit is already in history (by commit_id)
            last_commit_id = last_commit.get("commit_id")
            if last_commit_id and not any(c.get("commit_id") == last_commit_id for c in history):
                history.insert(0, last_commit)  # Add as most recent
        elif last_commit and not history:
            history = [last_commit]
        
        # Get max_commits config
        max_commits = get_max_commits_config(project_name)
        
        # Trim history to max_commits
        if len(history) > max_commits:
            history = history[:max_commits]
        
        # Create unified structure
        unified_data = {
            "version": "1.0",
            "last_commit": history[0] if history else None,
            "history": history,
            "max_commits": max_commits,
            "last_updated": datetime.now().isoformat() + "Z"
        }
        
        # Write unified file
        safe_write_json(unified_path, unified_data, create_backup=False)
        
        log_message(f"[CommitTracker] ✅ Migrated to unified format: {len(history)} commits")
        return True
        
    except Exception as e:
        log_message(f"[CommitTracker] ❌ Migration failed: {e}")
        return False


def generate_commit_report(project_name: str, commit_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Generate unified commit_history.json after Git commit.
    
    ✅ TASK 8.8: Structured commit metadata
    ✅ TASK 8.10.1: Unified commit_history.json (merged from commit_report.json + commit_history.jsonl)
    
    Args:
        project_name: Project name
        commit_id: Optional commit hash (if None, gets latest)
    
    Returns:
        dict: Commit report or None if error
    """
    try:
        project_path = f"projects/{project_name}"
        
        if not os.path.exists(project_path):
            return None
        
        # Get commit hash if not provided
        if not commit_id:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return None
            commit_id = result.stdout.strip()
        
        # Get commit message and files changed
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%s", "--name-only"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return None
        
        lines = result.stdout.strip().split("\n")
        commit_message = lines[0] if lines else "No message"
        files_changed = [f for f in lines[1:] if f.strip()] if len(lines) > 1 else []
        
        # ✅ TASK 8.10.1.1: Enhance commit summaries with file context
        file_contexts = {}
        for file_path in files_changed[:5]:  # Limit to first 5 files
            try:
                full_path = os.path.join(project_path, file_path)
                if os.path.isfile(full_path) and not file_path.startswith('.lazydeve/'):
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_lines = f.readlines()[:3]  # First 3 lines
                        file_contexts[file_path] = ''.join(file_lines).strip()[:100]  # Max 100 chars per file
            except Exception:
                # Skip files that can't be read (binary, permissions, etc.)
                continue
        
        # Build commit report
        commit_report = {
            "version": "1.0",  # ✅ TASK 8.8 COMPATIBILITY: Commit report versioning for RAG/MCP
            "commit_id": commit_id[:7],  # Short hash
            "commit_id_full": commit_id,
            "files_changed": files_changed,
            "file_contexts": file_contexts,  # ✅ TASK 8.10.1.1: File context previews
            "summary": commit_message,
            "timestamp": datetime.now().isoformat() + "Z",
            "project": project_name
        }
        
        # ✅ TASK 8.10.1: Write to unified commit_history.json
        unified_path = f"projects/{project_name}/.lazydeve/commit_history.json"
        
        # Load existing unified history (or migrate if needed)
        if not os.path.exists(unified_path):
            migrate_to_unified_commit_history(project_name)
        
        # Read existing unified history
        existing_data = safe_read_json(unified_path, {
            "version": "1.0",
            "last_commit": None,
            "history": [],
            "max_commits": get_max_commits_config(project_name),
            "last_updated": datetime.now().isoformat() + "Z"
        })
        
        # Get max_commits from config or existing data
        max_commits = existing_data.get("max_commits", get_max_commits_config(project_name))
        
        # Update unified structure
        history = existing_data.get("history", [])
        
        # ✅ Deduplication: Remove existing commit with same commit_id (if any)
        commit_id_full = commit_report.get("commit_id_full")
        if commit_id_full:
            history = [c for c in history if c.get("commit_id_full") != commit_id_full]
        
        # Prepend new commit to history (most recent first) - FIFO behavior
        history.insert(0, commit_report)
        
        # Trim to max_commits (FIFO: oldest commits removed when limit exceeded)
        if len(history) > max_commits:
            history = history[:max_commits]
        
        # Update unified data
        unified_data = {
            "version": "1.0",
            "last_commit": commit_report,  # ✅ Mark latest commit
            "history": history,
            "max_commits": max_commits,
            "last_updated": datetime.now().isoformat() + "Z"
        }
        
        # Write unified file
        safe_write_json(unified_path, unified_data, create_backup=False)
        
        # Update snapshot
        from core.context_sync import update_snapshot
        update_snapshot(project_name, {
            "last_commit": commit_id[:7],
            "pending_changes": False
        })
        
        log_message(f"[CommitTracker] ✅ Generated unified commit history: {commit_id[:7]} ({len(history)} commits)")
        return commit_report
        
    except Exception as e:
        log_message(f"[CommitTracker] Failed to generate commit report: {e}")
        return None


def is_major_commit(commit_report: Dict[str, Any]) -> bool:
    """
    Check if commit is "major" (warrants README update).
    
    ✅ TASK 8.8: Major commit detection
    
    Returns:
        bool: True if major commit
    """
    summary = commit_report.get("summary", "").lower()
    major_keywords = ["feat:", "refactor:", "major:", "breaking", "version"]
    return any(keyword in summary for keyword in major_keywords)


def load_commit_data(project_name: str) -> Dict[str, Any]:
    """
    Load unified commit_history.json structure.
    ✅ TASK 8.10.1: Unified commit history loader
    
    Args:
        project_name: Project name
        
    Returns:
        dict: Unified commit data structure with last_commit and history
    """
    unified_path = f"projects/{project_name}/.lazydeve/commit_history.json"
    
    # Try unified format first
    if os.path.exists(unified_path):
        try:
            data = safe_read_json(unified_path, {})
            if data.get("version") == "1.0" and "last_commit" in data:
                # Auto-sync if history is empty but Git has commits
                history = data.get("history", [])
                if not history or (not data.get("last_commit") and history == []):
                    sync_commit_history_from_git(project_name)
                    # Reload after sync
                    data = safe_read_json(unified_path, {})
                return data
        except Exception as e:
            log_message(f"[CommitTracker] ⚠️ Error reading unified format: {e}")
    
    # Fallback: migrate from old format
    if migrate_to_unified_commit_history(project_name):
        try:
            return safe_read_json(unified_path, {
                "version": "1.0",
                "last_commit": None,
                "history": [],
                "max_commits": 3,
                "last_updated": datetime.now().isoformat() + "Z"
            })
        except Exception:
            pass
    
    # Return empty structure if all else fails
    return {
        "version": "1.0",
        "last_commit": None,
        "history": [],
        "max_commits": 3,
        "last_updated": datetime.now().isoformat() + "Z"
    }


def load_last_commit_report(project_name: str) -> Optional[Dict[str, Any]]:
    """
    Load last commit report from unified commit_history.json.
    ✅ TASK 8.10.1: Backward compatible - reads from unified structure
    
    Args:
        project_name: Project name
        
    Returns:
        dict: Last commit report or None
    """
    try:
        commit_data = load_commit_data(project_name)
        return commit_data.get("last_commit")
    except Exception as e:
        log_message(f"[CommitTracker] ⚠️ Error loading last commit: {e}")
        # Fallback to old format for backward compatibility
        old_report_path = f"projects/{project_name}/.lazydeve/commit_report.json"
        if os.path.exists(old_report_path):
            try:
                return safe_read_json(old_report_path, None)
            except Exception:
                pass
        return None


def load_commit_history(project_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Load commit history from unified commit_history.json.
    ✅ TASK 8.10.1: Backward compatible - reads from unified structure
    
    Args:
        project_name: Project name
        limit: Maximum number of commits to return
    
    Returns:
        list: Commit reports (most recent first)
    """
    try:
        commit_data = load_commit_data(project_name)
        history = commit_data.get("history", [])
        # Return limited history (most recent first)
        return history[:limit]
    except Exception as e:
        log_message(f"[CommitTracker] ⚠️ Error loading commit history: {e}")
        # Fallback to old format for backward compatibility
        old_history_path = f"projects/{project_name}/.lazydeve/commit_history.jsonl"
        commits = []
        
        if os.path.exists(old_history_path):
            try:
                with open(old_history_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                for line in lines[-limit:]:
                    try:
                        commit = json.loads(line.strip())
                        commits.append(commit)
                    except json.JSONDecodeError:
                        continue
                
                return list(reversed(commits))
            except Exception:
                pass
        
        return []


def sync_commit_history_from_git(project_name: str) -> bool:
    """
    Sync commit_history.json from Git repository.
    Rebuilds commit history by scanning Git log for recent commits.
    ✅ TASK 8.10.1: Auto-sync for direct Git commits (outside API)
    
    Args:
        project_name: Project name
        
    Returns:
        bool: True if sync successful
    """
    try:
        project_path = f"projects/{project_name}"
        
        if not os.path.exists(project_path):
            return False
        
        # Check if Git repo exists
        git_dir = os.path.join(project_path, ".git")
        if not os.path.exists(git_dir):
            return False
        
        # Get max_commits config
        max_commits = get_max_commits_config(project_name)
        
        # Get recent commits from Git (up to max_commits)
        result = subprocess.run(
            ["git", "log", f"-{max_commits}", "--pretty=format:%H|%s", "--name-only"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            log_message(f"[CommitTracker] ⚠️ Git log failed for {project_name}")
            return False
        
        # Parse Git log output
        lines = result.stdout.strip().split("\n")
        if not lines or not lines[0]:
            # No commits found
            return False
        
        commits = []
        current_commit = None
        current_files = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a commit hash line (format: "hash|message")
            if "|" in line and len(line.split("|")[0]) == 40:
                # Save previous commit if exists
                if current_commit:
                    commits.append({
                        "version": "1.0",
                        "commit_id": current_commit["hash"][:7],
                        "commit_id_full": current_commit["hash"],
                        "files_changed": current_files,
                        "summary": current_commit["message"],
                        "timestamp": datetime.now().isoformat() + "Z",  # Approximate
                        "project": project_name
                    })
                
                # Parse new commit
                parts = line.split("|", 1)
                current_commit = {
                    "hash": parts[0],
                    "message": parts[1] if len(parts) > 1 else "No message"
                }
                current_files = []
            else:
                # This is a file path
                if current_commit and line:
                    current_files.append(line)
        
        # Add last commit
        if current_commit:
            commits.append({
                "version": "1.0",
                "commit_id": current_commit["hash"][:7],
                "commit_id_full": current_commit["hash"],
                "files_changed": current_files,
                "summary": current_commit["message"],
                "timestamp": datetime.now().isoformat() + "Z",
                "project": project_name
            })
        
        if not commits:
            return False
        
        # Trim to max_commits
        commits = commits[:max_commits]
        
        # Build unified structure
        unified_data = {
            "version": "1.0",
            "last_commit": commits[0] if commits else None,
            "history": commits,
            "max_commits": max_commits,
            "last_updated": datetime.now().isoformat() + "Z"
        }
        
        # Write unified file
        unified_path = f"projects/{project_name}/.lazydeve/commit_history.json"
        safe_write_json(unified_path, unified_data, create_backup=False)
        
        log_message(f"[CommitTracker] ✅ Synced commit history from Git: {len(commits)} commits for {project_name}")
        return True
        
    except Exception as e:
        log_message(f"[CommitTracker] ❌ Failed to sync commit history from Git: {e}")
        return False

