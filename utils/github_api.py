"""
GitHub API Utilities for LazyDeve
Handles repository creation, remote configuration, and error handling.
✅ TASK 4.2: GitHub API Automation
"""

import requests
import os
from typing import Optional, Dict
from core.config import GITHUB_TOKEN, GITHUB_USER
from core.basic_functional import log_message

GITHUB_API_BASE = "https://api.github.com"

def create_github_repository(
    repo_name: str,
    description: str = "",
    private: bool = False,
    auto_init: bool = False
) -> Dict:
    """
    Create a GitHub repository via API.
    
    Args:
        repo_name: Repository name (e.g., "lazydeve_MyProject")
        description: Repository description
        private: Whether repository is private (default: False)
        auto_init: Initialize with README (default: False)
    
    Returns:
        dict: {
            "status": "success" | "error",
            "repo_url": "https://github.com/user/repo.git" (if success),
            "error": "error message" (if error),
            "error_code": "AUTH_FAILED" | "NAME_CONFLICT" | "RATE_LIMIT" | "UNKNOWN"
        }
    """
    if not GITHUB_TOKEN:
        log_message("[GitHub] ⚠️ GITHUB_TOKEN not configured, skipping GitHub repo creation")
        return {
            "status": "error",
            "error": "GITHUB_TOKEN not configured",
            "error_code": "NO_TOKEN"
        }
    
    if not GITHUB_USER:
        log_message("[GitHub] ⚠️ GITHUB_USER not configured, skipping GitHub repo creation")
        return {
            "status": "error",
            "error": "GITHUB_USER not configured",
            "error_code": "NO_USER"
        }
    
    url = f"{GITHUB_API_BASE}/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": auto_init
    }
    
    try:
        log_message(f"[GitHub] Creating repository: {repo_name}")
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 201:
            repo_data = response.json()
            repo_url = repo_data.get("clone_url", "")
            log_message(f"[GitHub] ✅ Repository created: {repo_url}")
            return {
                "status": "success",
                "repo_url": repo_url,
                "repo_name": repo_name,
                "full_name": repo_data.get("full_name", "")
            }
        elif response.status_code == 401:
            log_message(f"[GitHub] ❌ Authentication failed: {response.text}")
            return {
                "status": "error",
                "error": "GitHub authentication failed",
                "error_code": "AUTH_FAILED"
            }
        elif response.status_code == 422:
            # Name conflict or validation error
            error_data = response.json()
            error_msg = error_data.get("message", "Repository creation failed")
            log_message(f"[GitHub] ❌ Repository creation failed: {error_msg}")
            
            if "name already exists" in error_msg.lower():
                return {
                    "status": "error",
                    "error": f"Repository '{repo_name}' already exists",
                    "error_code": "NAME_CONFLICT"
                }
            else:
                return {
                    "status": "error",
                    "error": error_msg,
                    "error_code": "VALIDATION_ERROR"
                }
        elif response.status_code == 403:
            # Rate limit or permissions
            rate_limit = response.headers.get("X-RateLimit-Remaining", "unknown")
            log_message(f"[GitHub] ❌ Rate limit or permission error: {response.text}")
            return {
                "status": "error",
                "error": "GitHub API rate limit exceeded or insufficient permissions",
                "error_code": "RATE_LIMIT",
                "rate_limit_remaining": rate_limit
            }
        else:
            log_message(f"[GitHub] ❌ Unexpected error: {response.status_code} - {response.text}")
            return {
                "status": "error",
                "error": f"GitHub API error: {response.status_code}",
                "error_code": "UNKNOWN",
                "response_text": response.text[:200]
            }
    
    except requests.exceptions.Timeout:
        log_message("[GitHub] ❌ Request timeout")
        return {
            "status": "error",
            "error": "GitHub API request timeout",
            "error_code": "TIMEOUT"
        }
    except requests.exceptions.RequestException as e:
        log_message(f"[GitHub] ❌ Request error: {e}")
        return {
            "status": "error",
            "error": f"GitHub API request failed: {str(e)}",
            "error_code": "REQUEST_ERROR"
        }
    except Exception as e:
        log_message(f"[GitHub] ❌ Unexpected error: {e}")
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNKNOWN"
        }

def check_repository_exists(repo_name: str) -> bool:
    """
    Check if a GitHub repository already exists.
    
    Args:
        repo_name: Repository name (e.g., "lazydeve_MyProject")
    
    Returns:
        bool: True if repository exists, False otherwise
    """
    if not GITHUB_TOKEN or not GITHUB_USER:
        return False
    
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_USER}/{repo_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def ensure_github_remote_exists(project_name: str, project_path: str) -> Dict:
    """
    Ensure GitHub remote exists for a project.
    If missing and allow_github_access=true, auto-creates and links the repository.
    
    This function is idempotent - safe to call multiple times.
    It checks if remote exists before attempting creation.
    
    ✅ TASK 4.2.3: Reusable helper for auto-creating GitHub repos for existing projects
    
    Args:
        project_name: Name of the project
        project_path: Path to project directory (e.g., "projects/ProjectName")
    
    Returns:
        dict: {
            "status": "exists" | "created" | "linked" | "disabled" | "error",
            "repo_url": "https://github.com/user/repo.git" (if created/linked),
            "message": "Human-readable message",
            "error": "error message" (if error)
        }
    """
    from core.config import allow_github_access, GITHUB_USER
    import subprocess
    
    if not allow_github_access:
        return {
            "status": "disabled",
            "message": "GitHub access disabled (allow_github_access=false)"
        }
    
    # Check if remote already exists
    remote_check = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if remote_check.returncode == 0:
        return {
            "status": "exists",
            "repo_url": remote_check.stdout.strip(),
            "message": "Remote already exists"
        }
    
    # No remote exists - create GitHub repo
    try:
        github_repo_name = f"lazydeve_{project_name}"
        
        # Check if repo already exists on GitHub
        if check_repository_exists(github_repo_name):
            # Repo exists, just link it
            repo_url = f"https://github.com/{GITHUB_USER}/{github_repo_name}.git"
            remote_add = subprocess.run(
                ["git", "remote", "add", "origin", repo_url],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if remote_add.returncode == 0:
                # Set upstream for main branch
                subprocess.run(
                    ["git", "branch", "-M", "main"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                log_message(f"[GitHub] ✅ Linked existing GitHub repository: {repo_url}")
                return {
                    "status": "linked",
                    "repo_url": repo_url,
                    "message": "Linked existing GitHub repository"
                }
            else:
                return {
                    "status": "error",
                    "error": f"Failed to link remote: {remote_add.stderr}"
                }
        else:
            # Create new GitHub repository
            github_result = create_github_repository(
                repo_name=github_repo_name,
                description=f"Auto-created for {project_name}",
                private=True,
                auto_init=False
            )
            
            if github_result["status"] == "success":
                repo_url = github_result["repo_url"]
                remote_add = subprocess.run(
                    ["git", "remote", "add", "origin", repo_url],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if remote_add.returncode == 0:
                    # Set upstream for main branch
                    subprocess.run(
                        ["git", "branch", "-M", "main"],
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    log_message(f"[GitHub] ✅ GitHub repository created and linked: {repo_url}")
                    return {
                        "status": "created",
                        "repo_url": repo_url,
                        "message": "GitHub repository created and linked"
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"Repository created but remote add failed: {remote_add.stderr}"
                    }
            else:
                return {
                    "status": "error",
                    "error": github_result.get("error", "Unknown error")
                }
    except Exception as e:
        log_message(f"[GitHub] ❌ Error ensuring GitHub remote: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

