"""
project_manager.py
------------------
Project Management Layer for LazyDeve Agent.
Handles multi-project management, active project tracking, and project operations.

✅ TASK 8.2 RESTORED: All functions restored from OLD_project_manager_before_task_7_split.py
- Functions were lost during Task 7 refactoring
- This restoration fixes AttributeError issues in /projects/* endpoints
- All Task 4, 5, 7 enhancements preserved

Features:
- Thread-safe state management
- Project name validation
- Error handling and backup system
- Git operations with proper directory context
- Comprehensive logging
"""

import os
import json
import requests
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8001/projects"  # Adjust the base URL as needed

# ============================================================
# TASK 8.2: HELPER FUNCTIONS (RESTORED)
# ============================================================

def check_project_exists(project_name: str) -> bool:
    """Check if a project exists via API endpoint."""
    response = requests.get(f"{BASE_URL}/list")
    if response.status_code == 200:
        projects = response.json()
        return project_name in projects
    return False

def create_project_structure(project_name: str):
    """Create basic project structure with .lazydeve directory."""
    project_path = os.path.join("projects", project_name)
    lazydeve_path = os.path.join(project_path, ".lazydeve")
    
    os.makedirs(lazydeve_path, exist_ok=True)
    
    config_path = os.path.join(lazydeve_path, "config.json")
    memory_path = os.path.join(lazydeve_path, "memory.json")
    logs_path = os.path.join(lazydeve_path, "logs")
    
    with open(config_path, 'w') as config_file:
        json.dump({}, config_file)  # Initialize with an empty config
    
    with open(memory_path, 'w') as memory_file:
        json.dump({"active_project": project_name}, memory_file)  # Initialize memory with active project
    
    # Set the active project in ContextManager singleton
    try:
        from core.context_manager import context_manager
        context_manager.set_project(project_name)
    except ImportError:
        pass  # ContextManager not available, continue with legacy behavior
    
    os.makedirs(logs_path, exist_ok=True)  # Create logs directory

def ensure_lazydeve_structure(project_name: str):
    """
    Task 7.7.6 — Refactor Project Initialization Pipeline
    Add sanity check and automatic .lazydeve/ bootstrapping.
    
    Args:
        project_name: Name of the project to ensure structure for
        
    Returns:
        dict: Result with status and message
    """
    try:
        from core.basic_functional import log_message
        
        base = f"projects/{project_name}/.lazydeve"
        
        # Create .lazydeve directory if it doesn't exist
        os.makedirs(base, exist_ok=True)
        
        # Create logs directory
        logs_dir = os.path.join(base, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Ensure required files exist
        required_files = ["memory.json", "config.json", "stats.json", "snapshot.json"]  # ✅ TASK 8.10.1.1: Added snapshot.json
        created_files = []
        
        for filename in required_files:
            file_path = os.path.join(base, filename)
            if not os.path.exists(file_path):
                # ✅ TASK 8.10.1.1: snapshot.json handled separately below with proper initialization
                if filename == "snapshot.json":
                    continue  # Skip - will be initialized below
                with open(file_path, "w", encoding="utf-8") as fp:
                    if filename == "memory.json":
                        json.dump({"project_name": project_name, "actions": [], "stats": {}}, fp)
                    elif filename == "config.json":
                        json.dump({"project_name": project_name, "created": datetime.now().isoformat()}, fp)
                    elif filename == "stats.json":
                        json.dump({"project_name": project_name, "status": "initialized"}, fp)
                created_files.append(filename)
        
        # ✅ TASK 8.10.1.1: Initialize snapshot.json during project creation
        snapshot_path = os.path.join(base, "snapshot.json")
        if not os.path.exists(snapshot_path):
            try:
                from core.context_sync import load_snapshot
                from core.memory_lock import safe_write_json
                default_snapshot = load_snapshot(project_name)  # Returns default structure
                safe_write_json(snapshot_path, default_snapshot, create_backup=False)
                created_files.append("snapshot.json")
                log_message(f"[ProjectManager] ✅ Initialized snapshot.json for {project_name}")
            except Exception as snapshot_error:
                log_message(f"[ProjectManager] ⚠️ Failed to initialize snapshot.json: {snapshot_error}")
        
        if created_files:
            log_message(f"[ProjectManager] Created missing .lazydeve files for '{project_name}': {', '.join(created_files)}")
            return {
                "status": "created", 
                "message": f"Created missing files: {', '.join(created_files)}",
                "created_files": created_files
            }
        else:
            log_message(f"[ProjectManager] .lazydeve structure already complete for '{project_name}'")
            return {
                "status": "exists", 
                "message": "All required .lazydeve files already exist",
                "created_files": []
            }
            
    except Exception as e:
        log_message(f"[ProjectManager] Error ensuring .lazydeve structure for '{project_name}': {e}")
        return {"status": "error", "message": f"Failed to ensure .lazydeve structure: {str(e)}"}

def validate_project_structure(project_name: str):
    """
    Task 7.7.6 — Validate existing project structure
    Check if a project has proper .lazydeve structure and fix if needed.
    
    Args:
        project_name: Name of the project to validate
        
    Returns:
        dict: Result with status and message
    """
    try:
        from core.basic_functional import log_message
        
        project_path = os.path.join("projects", project_name)
        if not os.path.exists(project_path):
            return {"status": "error", "message": f"Project '{project_name}' does not exist"}
        
        # Use ensure_lazydeve_structure to validate and fix if needed
        result = ensure_lazydeve_structure(project_name)
        
        if result["status"] == "created":
            log_message(f"[ProjectManager] Fixed incomplete .lazydeve structure for '{project_name}'")
            return {"status": "fixed", "message": f"Fixed missing files: {', '.join(result['created_files'])}"}
        else:
            log_message(f"[ProjectManager] Project '{project_name}' structure is valid")
            return {"status": "valid", "message": "Project structure is complete"}
            
    except Exception as e:
        log_message(f"[ProjectManager] Error validating project structure for '{project_name}': {e}")
        return {"status": "error", "message": f"Failed to validate project structure: {str(e)}"}

def ensure_project_exists(project_name: str):
    """Ensure project exists, create if not."""
    if not check_project_exists(project_name):
        create_project_structure(project_name)

# ============================================================
# TASK 8.2: MAIN PROJECT FUNCTIONS (RESTORED)
# ============================================================

def create_project(project_name: str, description: str = "New project", language: str = "generic", auto_sync: bool = True, create_github_repo: bool = False):
    """
    Create a new project with full structure and memory initialization.
    ✅ TASK 8.2 RESTORED from OLD_project_manager_before_task_7_split.py
    ✅ TASK 4.2 FIX: Single Flag GitHub Control Design
    
    Args:
        project_name: Name of the project
        description: Project description
        language: Programming language (default: generic)
        auto_sync: Automatically commit and push to GitHub (default: True)
        create_github_repo: Whether to create GitHub repository
                          - Note: This is now auto-determined from allow_github_access in .env
                          - API endpoint automatically sets this based on allow_github_access
                          - For internal use only (backward compatibility)
        
    Returns:
        dict: Result with status and message
        
    Behavior:
        - If allow_github_access=true: Automatically creates GitHub repository and pushes initial commit
        - If allow_github_access=false: Creates local Git repository only (no GitHub operations)
    """
    try:
        from core.basic_functional import log_message
        from core.memory_utils import init_project_memory
        
        log_message(f"[TASK 8.2 RESTORED] create_project() called for '{project_name}'")
        
        # Validate project name
        if not project_name or not project_name.strip():
            return {"status": "error", "message": "Project name cannot be empty"}
        
        # Check if project already exists
        project_path = os.path.join("projects", project_name)
        if os.path.exists(project_path):
            return {"status": "exists", "message": f"Project '{project_name}' already exists"}
        
        # Create project structure
        create_project_structure(project_name)
        
        # Task 7.7.6 — Add sanity check and automatic .lazydeve/ bootstrapping
        structure_result = ensure_lazydeve_structure(project_name)
        if structure_result["status"] == "error":
            return {"status": "error", "message": f"Failed to ensure .lazydeve structure: {structure_result['message']}"}
        
        log_message(f"[ProjectManager] .lazydeve structure validated for '{project_name}': {structure_result['message']}")
        
        # Create additional directories
        src_path = os.path.join(project_path, "src")
        tests_path = os.path.join(project_path, "tests")
        docs_path = os.path.join(project_path, "docs")
        
        os.makedirs(src_path, exist_ok=True)
        os.makedirs(tests_path, exist_ok=True)
        os.makedirs(docs_path, exist_ok=True)
        
        # Create README.md
        readme_path = os.path.join(project_path, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# {project_name}\n\n{description}\n\n## Project Structure\n\n- `src/` - Source code\n- `tests/` - Test files\n- `docs/` - Documentation\n- `.lazydeve/` - LazyDeve metadata\n")
        
        # Initialize project memory
        memory = init_project_memory(project_name, description)
        
        # Create action log file
        logs_path = os.path.join(project_path, ".lazydeve", "logs")
        action_log_path = os.path.join(logs_path, "actions.log")
        with open(action_log_path, "w", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] [INIT] Project '{project_name}' created\n")
        
        # Task 7.7.11-B — Add .gitkeep placeholders to ensure Git tracks empty directories
        # Git ignores empty directories, so we add .gitkeep to make them visible
        for subdir in ["src", "tests", "docs"]:
            keep_file = os.path.join(project_path, subdir, ".gitkeep")
            # Touch the file (create if doesn't exist)
            with open(keep_file, "a", encoding="utf-8") as f:
                pass  # Empty file
        
        log_message(f"[ProjectManager] Added .gitkeep placeholders to src/, tests/, docs/")
        log_message(f"[ProjectManager] Created project: {project_name}")
        
        # 🔒 TASK 4: Set as active project and persist for startup restoration
        try:
            from core.context_manager import context_manager, save_last_active_project
            context_manager.set_project(project_name)
            log_message(f"[ProjectManager] Set '{project_name}' as active project")
            
            # ✅ TASK 4: Save project context/memory immediately
            # Extract description from README.md if exists
            readme_path = os.path.join(project_path, "README.md")
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        readme_content = f.read()
                    # Update memory with README content
                    from core.memory_utils import update_memory
                    update_memory(project_name, "create", f"Project created: {description}", 
                                 extra={"readme_preview": readme_content[:500]})  # Store first 500 chars
                except Exception as readme_error:
                    log_message(f"[ProjectManager] Could not read README for context: {readme_error}")
            
            # ✅ TASK 4: Persist "last_active_project" for startup restoration
            save_last_active_project(project_name)
            log_message(f"[ProjectManager] ✅ Project '{project_name}' set as active and persisted")
        except Exception as ctx_error:
            log_message(f"[ProjectManager] Could not set active project: {ctx_error}")
        
        # ✅ TASK 3.6: Auto-Init Git Repository for New Project
        sync_status = "disabled"
        sync_details = {}
        
        try:
            import subprocess
            from utils.git_utils import safe_git_add, safe_git_commit
            
            # 🔴 CRITICAL SAFETY CHECK: Prevent Git re-initialization
            git_path = os.path.join(project_path, ".git")
            if os.path.exists(git_path):
                log_message(f"[ProjectManager] ⚠️ Git repo already exists for {project_name}, skipping initialization")
                sync_status = "already_initialized"
                sync_details["message"] = "Git repository already exists"
            else:
                # Initialize Git repository
                log_message(f"[ProjectManager] Initializing Git repository for: {project_name}")
                init_result = subprocess.run(
                    ["git", "init"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if init_result.returncode != 0:
                    log_message(f"[ProjectManager] ⚠️ Git init failed: {init_result.stderr}")
                    sync_status = "init_failed"
                    sync_details["error"] = init_result.stderr
                else:
                    log_message(f"[ProjectManager] ✅ Git repository initialized for {project_name}")
                    
                    # ✅ FIX: Rename branch to main (GitHub standard)
                    branch_rename = subprocess.run(
                        ["git", "branch", "-M", "main"],
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if branch_rename.returncode == 0:
                        log_message(f"[ProjectManager] ✅ Branch renamed to 'main'")
                    else:
                        log_message(f"[ProjectManager] ⚠️ Branch rename warning: {branch_rename.stderr}")
                    
                    # 🔐 Create .gitignore with secrets protection
                    gitignore_content = """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
venv/
.env

# Application logs (LazyDeve can read from file system)
logs/
*.log

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp

# Backups
*.bak
*.backup

# Aider temp files
.aider.*
.aider/

# 🔴 Secrets (CRITICAL)
.env
*.key
*.pem

# ⚠️ CRITICAL: DO NOT IGNORE .lazydeve/ — IT MUST BE TRACKED!
# .lazydeve/ contains context system data (memory, snapshots, events)
# and must be synced to Git for agent workflow
"""
                    gitignore_path = os.path.join(project_path, ".gitignore")
                    with open(gitignore_path, "w", encoding="utf-8") as f:
                        f.write(gitignore_content)
                    log_message(f"[ProjectManager] ✅ Created .gitignore with secrets protection")
                    
                    # Stage all files (including .lazydeve/)
                    add_result = safe_git_add(cwd=project_path)
                    if add_result["status"] == "success":
                        log_message(f"[ProjectManager] ✅ Git add successful for '{project_name}'")
                        sync_details["git_add"] = "success"
                        
                        # Initial commit
                        commit_msg = f"Initial commit - {project_name}"
                        commit_result = safe_git_commit(commit_msg, cwd=project_path)
                        
                        if commit_result["status"] == "success":
                            log_message(f"[ProjectManager] ✅ Initial commit created: {commit_msg}")
                            sync_details["git_commit"] = "success"
                            sync_status = "initialized"
                        else:
                            log_message(f"[ProjectManager] ⚠️ Initial commit failed: {commit_result.get('error', '')}")
                            sync_details["git_commit"] = "failed"
                            sync_details["commit_error"] = commit_result.get("error", "")
                            sync_status = "partial"
                    else:
                        log_message(f"[ProjectManager] ⚠️ Git add failed: {add_result.get('error', '')}")
                        sync_details["git_add"] = "failed"
                        sync_details["add_error"] = add_result.get("error", "")
                        sync_status = "partial"
                    
                    # Store git_repo_path in config.json
                    config_path = os.path.join(project_path, ".lazydeve", "config.json")
                    if os.path.exists(config_path):
                        try:
                            with open(config_path, "r", encoding="utf-8") as f:
                                config = json.load(f)
                            config["git_repo_path"] = os.path.abspath(project_path)
                            config["git_initialized"] = datetime.now().isoformat()
                            with open(config_path, "w", encoding="utf-8") as f:
                                json.dump(config, f, indent=2, ensure_ascii=False)
                            log_message(f"[ProjectManager] ✅ Stored git_repo_path in config.json")
                        except Exception as config_error:
                            log_message(f"[ProjectManager] ⚠️ Could not update config.json: {config_error}")
                    else:
                        # Create config.json if it doesn't exist
                        config = {
                            "project_name": project_name,
                            "git_repo_path": os.path.abspath(project_path),
                            "git_initialized": datetime.now().isoformat(),
                            "created": datetime.now().isoformat()
                        }
                        try:
                            with open(config_path, "w", encoding="utf-8") as f:
                                json.dump(config, f, indent=2, ensure_ascii=False)
                            log_message(f"[ProjectManager] ✅ Created config.json with git_repo_path")
                        except Exception as config_error:
                            log_message(f"[ProjectManager] ⚠️ Could not create config.json: {config_error}")
                    
        except subprocess.TimeoutExpired:
            log_message(f"[ProjectManager] ⚠️ Git operation timed out for '{project_name}'")
            sync_status = "timeout"
            sync_details["error"] = "Git operation timed out"
        except Exception as git_error:
            log_message(f"[ProjectManager] ⚠️ Git initialization error: {git_error}")
            sync_status = "error"
            sync_details["error"] = str(git_error)
        
        # ============================================================
        # ✅ TASK 4.2 FIX: Single Flag GitHub Control Design
        # GitHub behavior controlled entirely by allow_github_access
        # ============================================================
        github_status = "disabled"
        github_details = {}
        
        # Check if GitHub access is allowed via environment
        from core.config import allow_github_access
        
        # ✅ SIMPLIFIED: Single source of truth - allow_github_access controls all GitHub operations
        # - allow_github_access=true → Automatically create GitHub repo and push initial commit
        # - allow_github_access=false → Local-only mode (no GitHub operations)
        if allow_github_access:
            try:
                from utils.github_api import create_github_repository, check_repository_exists
                from core.config import GITHUB_USER
                from utils.git_utils import safe_git_push
                import subprocess
                
                # Generate repository name: lazydeve_<project_name>
                github_repo_name = f"lazydeve_{project_name}"
                
                # Check if repo already exists
                if check_repository_exists(github_repo_name):
                    log_message(f"[GitHub] ⚠️ Repository '{github_repo_name}' already exists, skipping creation")
                    github_status = "already_exists"
                    github_details["message"] = f"Repository '{github_repo_name}' already exists on GitHub"
                    github_details["repo_name"] = github_repo_name
                else:
                    # Create GitHub repository
                    github_result = create_github_repository(
                        repo_name=github_repo_name,
                        description=description,
                        private=True,  # ✅ FIX: Create as private by default (security)
                        auto_init=False  # We'll push our own initial commit
                    )
                    
                    if github_result["status"] == "success":
                        repo_url = github_result["repo_url"]
                        log_message(f"[GitHub] ✅ Repository created: {repo_url}")
                        
                        # Configure Git remote
                        try:
                            # Check if remote already exists
                            remote_check = subprocess.run(
                                ["git", "remote", "get-url", "origin"],
                                cwd=project_path,
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            
                            if remote_check.returncode == 0:
                                log_message(f"[GitHub] ⚠️ Remote 'origin' already exists: {remote_check.stdout.strip()}")
                                github_status = "remote_exists"
                                github_details["message"] = "Remote 'origin' already configured"
                                github_details["existing_remote"] = remote_check.stdout.strip()
                            else:
                                # Add remote
                                remote_add = subprocess.run(
                                    ["git", "remote", "add", "origin", repo_url],
                                    cwd=project_path,
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                
                                if remote_add.returncode == 0:
                                    log_message(f"[GitHub] ✅ Remote 'origin' configured: {repo_url}")
                                    
                                    # Push initial commit (only if Git was successfully initialized)
                                    if sync_status == "initialized":
                                        # ✅ FIX: Use -u flag to set upstream branch tracking
                                        push_result = subprocess.run(
                                            ["git", "push", "-u", "origin", "main"],
                                            cwd=project_path,
                                            capture_output=True,
                                            text=True,
                                            timeout=30
                                        )
                                        
                                        if push_result.returncode == 0:
                                            log_message(f"[GitHub] ✅ Initial commit pushed to GitHub with upstream tracking")
                                            github_status = "created_and_pushed"
                                            github_details["repo_url"] = repo_url
                                            github_details["repo_name"] = github_repo_name
                                            github_details["push_status"] = "success"
                                        else:
                                            # If push fails, try without -u flag as fallback
                                            log_message(f"[GitHub] ⚠️ Push with -u failed, trying without upstream tracking...")
                                            fallback_push = safe_git_push(branch="main", cwd=project_path)
                                            
                                            if fallback_push["status"] == "success":
                                                log_message(f"[GitHub] ✅ Initial commit pushed to GitHub (without upstream)")
                                                github_status = "created_and_pushed"
                                                github_details["repo_url"] = repo_url
                                                github_details["repo_name"] = github_repo_name
                                                github_details["push_status"] = "success"
                                            else:
                                                log_message(f"[GitHub] ⚠️ Repository created but push failed: {fallback_push.get('error', push_result.stderr)}")
                                                github_status = "created_not_pushed"
                                                github_details["repo_url"] = repo_url
                                                github_details["repo_name"] = github_repo_name
                                                github_details["push_status"] = "failed"
                                                github_details["push_error"] = fallback_push.get("error", push_result.stderr)
                                    else:
                                        log_message(f"[GitHub] ⚠️ Repository created but Git not initialized, skipping push")
                                        github_status = "created_not_pushed"
                                        github_details["repo_url"] = repo_url
                                        github_details["repo_name"] = github_repo_name
                                        github_details["push_status"] = "skipped"
                                        github_details["push_reason"] = "Git not initialized"
                                else:
                                    log_message(f"[GitHub] ⚠️ Repository created but remote configuration failed: {remote_add.stderr}")
                                    github_status = "created_not_configured"
                                    github_details["repo_url"] = repo_url
                                    github_details["repo_name"] = github_repo_name
                                    github_details["remote_error"] = remote_add.stderr
                        except subprocess.TimeoutExpired:
                            log_message(f"[GitHub] ⚠️ Git remote operation timed out")
                            github_status = "created_timeout"
                            github_details["repo_url"] = repo_url
                            github_details["error"] = "Git remote operation timed out"
                        except Exception as git_error:
                            log_message(f"[GitHub] ⚠️ Git remote configuration error: {git_error}")
                            github_status = "created_not_configured"
                            github_details["repo_url"] = repo_url
                            github_details["error"] = str(git_error)
                    else:
                        # GitHub API failed, but project creation continues
                        error_code = github_result.get("error_code", "UNKNOWN")
                        error_msg = github_result.get("error", "Unknown error")
                        log_message(f"[GitHub] ⚠️ GitHub repository creation failed: {error_msg}")
                        github_status = "failed"
                        github_details["error"] = error_msg
                        github_details["error_code"] = error_code
                        
                        # Don't fail project creation - just log the error
                        # User can manually create repo later
            
            except ImportError:
                log_message("[GitHub] ⚠️ GitHub API utilities not available")
                github_status = "not_available"
                github_details["error"] = "GitHub API utilities not available"
            except Exception as github_error:
                log_message(f"[GitHub] ⚠️ Unexpected GitHub integration error: {github_error}")
                github_status = "error"
                github_details["error"] = str(github_error)
                # Don't fail project creation - just log the error
        else:
            # ✅ GitHub access disabled - local-only mode
            github_status = "disabled"
            github_details["message"] = "GitHub access disabled (allow_github_access=false) - local-only mode"
        
        # Task 7.7.11-B (Enhanced) — Event Bus & Memory Hooks Integration
        # Trigger events and update memory for Task 8 semantic context
        try:
            from core.event_bus import trigger_event
            from core.memory_utils import update_memory, log_project_action
            
            # Log action to project action log
            log_project_action(project_name, "create", f"Project initialized: {description[:80]}")
            
            # Update project memory with creation action
            update_memory(
                project_name, 
                "create", 
                f"Project created: {description[:50]}",
                extra={
                    "language": language,
                    "sync_status": sync_status,
                    "structure": ["src", "tests", "docs", ".lazydeve"]
                }
            )
            
            # Trigger post_action event (consistent with /execute, /commit patterns)
            trigger_event(
                "post_action",
                async_mode=True,
                project=project_name,
                action="create_project",
                details=f"Created project: {project_name}",
                success=True,
                sync_status=sync_status,
                description=description,
                language=language
            )
            
            # Trigger specific project_created event for future hooks
            trigger_event(
                "project_created",
                async_mode=True,
                project=project_name,
                description=description,
                language=language,
                sync_status=sync_status,
                structure={
                    "directories": ["src", "tests", "docs", ".lazydeve"],
                    "files": ["README.md", ".gitkeep"]
                }
            )
            
            log_message(f"[ProjectManager] Event hooks and memory updated for '{project_name}'")
            
        except Exception as hook_error:
            # Don't fail project creation if event/memory hooks fail
            log_message(f"[ProjectManager] Event/memory hook error (non-critical): {hook_error}")
        
        return {
            "status": "created",
            "message": f"Project '{project_name}' created successfully",
            "project_name": project_name,
            "description": description,
            "language": language,
            "sync_status": sync_status,
            "sync_details": sync_details,
            "github_status": github_status,  # ✅ TASK 4.2: GitHub integration status
            "github_details": github_details  # ✅ TASK 4.2: GitHub integration details
        }
        
    except Exception as e:
        log_message(f"[ProjectManager] Error creating project '{project_name}': {e}")
        return {"status": "error", "message": f"Failed to create project: {str(e)}"}

def commit_project(message: str, project_name: str = None):
    """
    Commit changes to a project.
    ✅ TASK 8.2 RESTORED from OLD_project_manager_before_task_7_split.py
    ✅ TASK 3.2: Updated to use cwd parameter instead of os.chdir()
    
    Args:
        message: Commit message
        project_name: Project name (optional, uses active project if not specified)
        
    Returns:
        dict: Result with status and message
    """
    try:
        from core.basic_functional import log_message
        from core.context_manager import context_manager
        from utils.git_utils import safe_git_add, safe_git_commit
        
        log_message(f"[TASK 8.2 RESTORED] commit_project() called")
        
        if not project_name:
            project_name = context_manager.get_project()  # 🔒 TASK 1 FIX: Use context manager instead of default
        
        if not project_name:
            return {"status": "error", "message": "No project specified and no active project set"}
        
        project_path = os.path.join("projects", project_name)
        if not os.path.exists(project_path):
            return {"status": "error", "message": f"Project '{project_name}' not found"}
        
        # ✅ TASK 3.2: Use cwd parameter instead of os.chdir()
        log_message(f"[ProjectManager] Committing to project '{project_name}' using cwd={project_path}")
        
        # Git add all changes
        add_result = safe_git_add(cwd=project_path)
        if add_result["status"] != "success":
            log_message(f"[ProjectManager] Git add failed: {add_result.get('error', 'Unknown error')}")
            return {"status": "error", "message": f"Git add failed: {add_result.get('error', 'Unknown error')}"}
        
        # Git commit
        commit_result = safe_git_commit(message, cwd=project_path)
        if commit_result["status"] == "success":
            log_message(f"[ProjectManager] Committed changes to project '{project_name}': {message}")
            
            # Store git_repo_path in config.json if not already present
            config_path = os.path.join(project_path, ".lazydeve", "config.json")
            if os.path.exists(config_path):
                try:
                    import json
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    
                    if "git_repo_path" not in config:
                        config["git_repo_path"] = os.path.abspath(project_path)
                        with open(config_path, "w", encoding="utf-8") as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                        log_message(f"[ProjectManager] Added git_repo_path to config: {config['git_repo_path']}")
                except Exception as config_error:
                    log_message(f"[ProjectManager] Warning: Could not update config.json: {config_error}")
            
            return {"status": "success", "message": f"Changes committed to '{project_name}'"}
        else:
            error_msg = commit_result.get("error", "Unknown error")
            log_message(f"[ProjectManager] Commit failed: {error_msg}")
            return {"status": "error", "message": f"Commit failed: {error_msg}"}
            
    except Exception as e:
        log_message(f"[ProjectManager] Error committing to project '{project_name}': {e}")
        return {"status": "error", "message": f"Failed to commit: {str(e)}"}

def list_projects() -> list:
    """
    List all projects in the 'projects' directory.
    ✅ TASK 8.2 FIXED: Removed hardcoded path, now scans actual projects directory
    ✅ Task 5: Explicitly exclude .trash directory
    
    Returns:
        list: List of project names
    """
    try:
        from core.basic_functional import log_message
        
        log_message(f"[TASK 8.2 RESTORED] list_projects() called")
        
        projects_dir = "projects"
        if not os.path.exists(projects_dir):
            os.makedirs(projects_dir, exist_ok=True)
            return []
        
        projects = [
            d for d in os.listdir(projects_dir)
            if os.path.isdir(os.path.join(projects_dir, d)) 
            and not d.startswith(".")
            and d != ".trash"  # ✅ Task 5: Explicitly exclude trash directory
        ]
        log_message(f"[ProjectManager] Found {len(projects)} projects: {projects}")
        return projects
    except Exception as e:
        from core.basic_functional import log_message
        log_message(f"[ProjectManager] Error listing projects: {e}")
        return []

def get_active_project() -> str:
    """
    Get the currently active project.
    ✅ TASK 8.2 RESTORED from OLD_project_manager_before_task_7_split.py
    
    Returns:
        str: Active project name, or None if no project is set
    """
    try:
        from core.basic_functional import log_message
        from core.context_manager import context_manager
        
        active = context_manager.get_project()
        log_message(f"[ProjectManager] Active project: {active}")
        return active
    except Exception as e:
        from core.basic_functional import log_message
        log_message(f"[ProjectManager] Error getting active project: {e}")
        return None

def set_active_project(name: str) -> dict:
    """
    Set the active project using ContextManager.
    ✅ TASK 8.2 RESTORED from OLD_project_manager_before_task_7_split.py
    ✅ TASK 4 ENHANCED: Now persists for startup restoration
    
    Args:
        name: Project name to set as active
        
    Returns:
        dict: Status result with active_project or error message
    """
    try:
        from core.basic_functional import log_message
        from core.context_manager import context_manager
        
        log_message(f"[TASK 8.2 RESTORED] set_active_project() called for '{name}'")
        
        # Validate project exists
        project_path = os.path.join("projects", name)
        if not os.path.exists(project_path):
            return {"status": "error", "message": f"Project '{name}' not found"}
        
        # Set active project in ContextManager
        context_manager.set_project(name)
        
        # ✅ TASK 4: Persist for startup restoration
        from core.context_manager import save_last_active_project
        save_last_active_project(name)
        
        # ✅ TASK 8.9: Initialize context on project switch
        try:
            from core.context_initializer import initialize_context_on_project_switch
            init_result = initialize_context_on_project_switch(name)
            if init_result:
                log_message(f"[ProjectManager] ✅ Context initialized for {name}")
            else:
                log_message(f"[ProjectManager] ⚠️ Context initialization returned None for {name}")
        except Exception as init_error:
            log_message(f"[ProjectManager] ⚠️ Context initialization failed: {init_error}")
        
        log_message(f"[ProjectManager] Set active project: {name} (persisted for startup)")
        return {"status": "success", "active_project": name}
    except Exception as e:
        from core.basic_functional import log_message
        log_message(f"[ProjectManager] Error setting active project: {e}")
        return {"status": "error", "message": str(e)}

def get_project_info(name: str) -> dict:
    """
    Get metadata for a specific project.
    ✅ TASK 8.2 RESTORED from OLD_project_manager_before_task_7_split.py
    
    Args:
        name: Project name
        
    Returns:
        dict: Project information with status, name, path, is_active, and file count
    """
    try:
        from core.basic_functional import log_message
        
        log_message(f"[TASK 8.2 RESTORED] get_project_info() called for '{name}'")
        
        path = os.path.join("projects", name)
        if not os.path.exists(path):
            return {"status": "error", "message": f"Project '{name}' not found"}
        
        # Count only non-hidden files and directories (filter out .git, __pycache__, etc.)
        files = [
            f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and not f.startswith(".")
        ]
        
        info = {
            "name": name,
            "path": os.path.abspath(path),
            "is_active": (get_active_project() == name),
            "files": len(files),
        }
        
        log_message(f"[ProjectManager] Retrieved info for project: {name}")
        return {"status": "ok", "info": info}
    except Exception as e:
        from core.basic_functional import log_message
        log_message(f"[ProjectManager] Error reading project info: {e}")
        return {"status": "error", "message": str(e)}

def archive_project(project_name: str) -> dict:
    """
    Safely moves a project folder from /projects/<name> to /projects/.trash/<name>.
    Uses absolute paths for reliability across all OS environments.
    ✅ TASK 8.2 RESTORED from OLD_project_manager_before_task_7_split.py
    ✅ Task 5: Safe project archivation system with comprehensive validation
    
    Args:
        project_name: Name of the project to archive
        
    Returns:
        dict: Result with status, project name, archive path, and was_active flag
    """
    from core.context_manager import context_manager
    from core.basic_functional import log_message
    
    log_message(f"[TASK 8.2 RESTORED] archive_project() called for '{project_name}'")
    
    # ✅ Task 5: Use absolute paths based on file location
    # This ensures reliable behavior regardless of where the agent is launched
    base_dir = Path(__file__).resolve().parent.parent
    projects_dir = base_dir / "projects"
    trash_dir = projects_dir / ".trash"
    src_path = projects_dir / project_name
    dst_path = trash_dir / project_name
    
    # ✅ Task 5: Log resolved paths for debugging
    log_message(f"[Archive] 📍 Path Resolution:")
    log_message(f"[Archive]   Base directory: {base_dir}")
    log_message(f"[Archive]   Projects directory: {projects_dir}")
    log_message(f"[Archive]   Trash directory: {trash_dir}")
    log_message(f"[Archive]   Source path: {src_path}")
    log_message(f"[Archive]   Destination path: {dst_path}")
    
    # ✅ Task 5: Validate project name format (security: prevent path injection)
    if not project_name or not re.match(r'^[a-zA-Z0-9_-]+$', project_name):
        return {
            "status": "error",
            "message": f"Invalid project name: '{project_name}'. Only alphanumeric, underscore, and hyphen allowed.",
            "error_code": "INVALID_NAME"
        }
    
    # ✅ Task 5: Validate projects directory exists
    if not projects_dir.exists():
        log_message(f"[Archive] ❌ Projects directory does not exist: {projects_dir}")
        return {
            "status": "error",
            "message": f"Projects directory not found: {projects_dir}",
            "error_code": "PROJECTS_DIR_NOT_FOUND",
            "resolved_path": str(projects_dir)
        }
    
    if not projects_dir.is_dir():
        log_message(f"[Archive] ❌ Projects path is not a directory: {projects_dir}")
        return {
            "status": "error",
            "message": f"Projects path exists but is not a directory: {projects_dir}",
            "error_code": "PROJECTS_DIR_INVALID",
            "resolved_path": str(projects_dir)
        }
    
    # ✅ Task 5: Verify source exists before proceeding
    if not src_path.exists():
        log_message(f"[Archive] ❌ Source project not found: {src_path}")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found at {src_path}",
            "error_code": "PROJECT_NOT_FOUND",
            "resolved_path": str(src_path)
        }
    
    if not src_path.is_dir():
        log_message(f"[Archive] ❌ Source path is not a directory: {src_path}")
        return {
            "status": "error",
            "message": f"Project path exists but is not a directory: {src_path}",
            "error_code": "PROJECT_PATH_INVALID",
            "resolved_path": str(src_path)
        }
    
    # ✅ Task 5: Check if project is active BEFORE archiving
    active_project = context_manager.get_project()
    was_active = (active_project == project_name)
    
    # ✅ Task 5: Prevent archiving active project
    if was_active:
        return {
            "status": "error",
            "error_code": "ACTIVE_PROJECT",
            "message": f"Cannot archive active project '{project_name}'. Set a different project as active first.",
            "suggestion": "Use /projects/set-active/{name} to switch to another project first"
        }
    
    # ✅ Task 5: Create .trash directory recursively with absolute path
    try:
        trash_dir.mkdir(parents=True, exist_ok=True)
        log_message(f"[Archive] ✅ Trash directory ready: {trash_dir}")
        if not trash_dir.exists():
            log_message(f"[Archive] ⚠️ Warning: Trash directory creation reported success but path does not exist")
            return {
                "status": "error",
                "message": f"Failed to create trash directory: {trash_dir}",
                "error_code": "TRASH_DIR_CREATION_FAILED",
                "resolved_path": str(trash_dir)
            }
    except Exception as e:
        log_message(f"[Archive] ❌ Failed to create .trash directory: {e}")
        log_message(f"[Archive]   Attempted path: {trash_dir}")
        return {
            "status": "error",
            "message": f"Failed to create archive directory: {str(e)}",
            "error_code": "ARCHIVE_FAILED",
            "resolved_path": str(trash_dir)
        }
    
    # ✅ Task 5: Remove existing target before moving (cleaner than timestamp)
    if dst_path.exists():
        try:
            shutil.rmtree(dst_path)
            log_message(f"[Archive] Removed existing archive: {dst_path}")
        except Exception as e:
            log_message(f"[Archive] Warning: Could not remove existing archive: {e}")
            # Fallback to timestamp if removal fails
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst_path = trash_dir / f"{project_name}_{timestamp}"
            log_message(f"[Archive] Using timestamped path as fallback: {dst_path}")
    
    # ✅ Task 5: Move project to trash
    try:
        log_message(f"[Archive] 🚀 Starting move operation:")
        log_message(f"[Archive]   From: {src_path}")
        log_message(f"[Archive]   To: {dst_path}")
        
        # Verify source still exists before move
        if not src_path.exists():
            log_message(f"[Archive] ❌ Source disappeared before move: {src_path}")
            return {
                "status": "error",
                "message": f"Source project no longer exists: {src_path}",
                "error_code": "SOURCE_MISSING",
                "resolved_path": str(src_path)
            }
        
        shutil.move(str(src_path), str(dst_path))
        
        # ✅ Task 5: Verify move succeeded
        if not dst_path.exists():
            log_message(f"[Archive] ❌ Move reported success but destination does not exist: {dst_path}")
            return {
                "status": "error",
                "message": f"Move operation failed: destination not found at {dst_path}",
                "error_code": "MOVE_VERIFICATION_FAILED",
                "resolved_path": str(dst_path)
            }
        
        if src_path.exists():
            log_message(f"[Archive] ⚠️ Warning: Move reported success but source still exists: {src_path}")
        
        log_message(f"[Archive] ✅ ARCHIVED PROJECT: {project_name}")
        log_message(f"[Archive]   Source: {src_path} (removed)")
        log_message(f"[Archive]   Destination: {dst_path} (verified)")
        
        # ============================================================
        # ✅ TASK 4.2: Check for GitHub remote and show message
        # ============================================================
        github_remote_info = None
        try:
            import subprocess
            remote_check = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=dst_path,  # Check in archived location
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if remote_check.returncode == 0:
                remote_url = remote_check.stdout.strip()
                github_remote_info = {
                    "has_remote": True,
                    "remote_url": remote_url,
                    "message": "Remote repository still exists on GitHub. Delete manually if no longer needed."
                }
                log_message(f"[Archive] ℹ️ Project has GitHub remote: {remote_url}")
            else:
                github_remote_info = {
                    "has_remote": False,
                    "message": "No GitHub remote configured"
                }
        except Exception as remote_error:
            log_message(f"[Archive] ⚠️ Could not check GitHub remote: {remote_error}")
            github_remote_info = {
                "has_remote": "unknown",
                "message": "Could not determine GitHub remote status"
            }
        
        return {
            "status": "archived",
            "project": project_name,
            "path": str(dst_path),
            "message": f"Project '{project_name}' archived successfully",
            "was_active": was_active,  # Flag for response handling (should always be False)
            "requires_project_selection": was_active,  # Should always be False
            "resolved_paths": {
                "source": str(src_path),
                "destination": str(dst_path),
                "projects_dir": str(projects_dir),
                "trash_dir": str(trash_dir)
            },
            "github_remote": github_remote_info  # ✅ TASK 4.2: GitHub remote information
        }
    except PermissionError as e:
        log_message(f"[Archive] ❌ Permission denied: {e}")
        return {
            "status": "error",
            "message": f"Permission denied: {str(e)}",
            "error_code": "PERMISSION_DENIED"
        }
    except Exception as e:
        log_message(f"[Archive] ❌ Failed to archive project '{project_name}': {e}")
        return {
            "status": "error",
            "message": f"Failed to archive project: {str(e)}",
            "error_code": "ARCHIVE_FAILED"
        }

# ============================================================
# TASK 8.2: ADDITIONAL HELPER (RESTORED)
# ============================================================

def create_multiple_projects(project_names: list, description: str = "New project", language: str = "generic"):
    """
    Create multiple new projects with full structure and memory initialization.
    ✅ TASK 8.2 RESTORED from OLD_project_manager_before_task_7_split.py
    
    Args:
        project_names: List of project names
        description: Project description
        language: Programming language (default: generic)
        
    Returns:
        list: Results for each project creation
    """
    results = []
    for project_name in project_names:
        result = create_project(project_name, description, language)
        results.append(result)
    return results
