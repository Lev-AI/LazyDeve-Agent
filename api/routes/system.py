"""
System Routes - System health and monitoring endpoints
Extracted from agent.py for Task 7 Phase 2
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response
from fastapi.openapi.utils import get_openapi
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any
from core.basic_functional import log_message
from core.context_manager import get_context_summary
from core.config import PUBLIC_AGENT_URL

router = APIRouter()


@router.get("/ping-agent")
def ping():
    """Health check endpoint - returns agent status."""
    return {"agent": "online", "cloudflare_url": PUBLIC_AGENT_URL}


@router.get("/logs")
def logs(project: str = Query("default"), lines: int = Query(200, ge=1, le=5000)):
    """
    Retrieve log files for a specific project or default agent logs.
    Returns last N lines of the log file.
    """
    try:
        log_path = f"logs/{project}.log" if project != "default" else "logs/agent.log"
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return {"status": "success", "logs": last_lines, "total_lines": len(all_lines)}
        else:
            return {"status": "error", "message": f"Log file {log_path} not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/ping-memory")
def ping_memory(project: str = Query(None)):  # 🔒 TASK 1 FIX: No default - use context manager
    """
    Memory sync check endpoint - verifies session context status using context manager.
    Returns information about the last GitHub sync and context freshness.
    """
    try:
        # 🔒 TASK 1 FIX: Use context manager if project not provided
        from core.context_manager import context_manager
        if not project:
            project = context_manager.get_project()
        
        if not project:
            return {
                "status": "error",
                "error": "No project specified and no active project set",
                "message": "Provide project parameter or set active project via /projects/set-active/{name}"
            }
        
        # Use context manager to get summary
        summary = get_context_summary(project)
        
        # Log the memory check
        status_msg = "OK" if summary["status"] == "ok" else "STALE"
        log_message(f"[Agent] Memory sync check: {status_msg}")
        
        return summary
        
    except Exception as e:
        print(f"[Agent] Memory check failed: {e}")
        return {
            "project": project,
            "last_sync": None,
            "commits_cached": 0,
            "files_cached": 0,
            "status": "error",
            "error": str(e)
        }


@router.get("/openapi.yaml", response_class=Response)
def openapi_schema():
    """
    Generate OpenAPI schema for ChatGPT Apps integration.
    Includes all endpoints: /status, /commits, /list-files, and others.
    
    Note: This imports 'app' from agent module to access all routes.
    """
    from agent import app  # Import here to avoid circular dependency
    
    # Generate OpenAPI schema dict (same pattern as other endpoints)
    openapi_dict = get_openapi(
        title="LazyDeve Agent API",
        version="1.5.0",
        description="""LazyDeve Agent API (v1.5.0) — Autonomous Development Agent

This schema reflects the current dynamic API used by ChatGPT Actions and tooling.

Major Endpoints:
- /status        → Git repository status and agent freshness (per-project)
- /commits       → Recent Git commit history (per-project)
- /list-files    → Recursive project file listing
- /execute       → Execute development tasks via Aider (code generation, refactoring) and handle file deletions (physical deletion + Git sync)
- /ping-agent    → Health check
- /update-file   → Update/clear file content (per-project)
- /read-file     → Read file content

Git Endpoints (Per-Project):
- /commit        → Commit changes to active project's Git repository (defaults to active project, or specify via 'project' parameter)
- /sync          → Sync active project with remote repository (git pull)
- /status        → Get Git status for active project (branch, last commit, etc.)
- /commits       → Get commit history for active project

Context Endpoints (Task 8.8 & 8.10.1.1 & 8.10.1.2):
- /api/v1/context/full/{project} → Get unified full context (context_full.json structure - all memory sources merged: commits, activity, snapshot, config, stats, user_memory, README preview)
- /projects/active → Get active project and full unified context (context_full.json format - automatically injected to ChatGPT)
- /projects/set-active/{name} → Switch project and get full unified context (context_full.json format)
- /api/v1/context/{project}/user-memory → Save persistent user notes to project context (max 300 chars, stored in config.json)
- /api/v1/context/summary/{project} → Get AI-ready context summary (minimal format for backward compatibility)
- /api/v1/context/detailed/{project} → Get detailed AI context (includes activity, commits, suggestions)
- /api/v1/context/llm/{project} → Get LLM-optimized context (README prepended to context_string)
- /context/snapshot → Get project state snapshot (last_run, last_commit, status, pending_changes)
- /context/events  → Query event history (run_logged, commit_synced, file_updated, etc.)
- /context/commits → Get commit reports and history (with metadata and file changes)

Per-Project Git Architecture:
Each project has its own isolated Git repository. All Git operations (commit, sync, status) 
operate within the active project's repository. The root repository tracks only agent code.

Authentication:
Bearer token is documented but not enforced yet (planned upgrade).

Usage:
For ChatGPT Actions, set the Schema URL to this endpoint (/openapi.yaml).""",
        routes=app.routes,
        servers=[
            {"url": "https://agent.lazydeve.uk", "description": "Production server"},
            {"url": "http://localhost:8001", "description": "Development server"}
        ]
    )
    
    # Convert to YAML (like other endpoints, but with YAML conversion)
    yaml_content = yaml.dump(openapi_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    # Return YAML response (similar pattern to other endpoints)
    return Response(
        content=yaml_content,
        media_type="application/x-yaml"
    )


@router.get("/routing-guide")
def get_routing_guide():
    """
    Returns endpoint routing rules for agent guidance.
    ✅ TASK 8.5: Endpoint routing documentation
    
    This endpoint provides programmatic access to routing rules,
    helping ChatGPT, MCP servers, and other agents select the correct endpoint.
    
    Returns:
        JSON object with routing rules, error handling patterns, and examples
    """
    routing_rules = {
        "version": "1.0",
        "schema_version": "1.0",
        "last_updated": "2025-11-17",
        "routing_rules": {
            "file_operations": {
                "create": {
                    "endpoint": "/update-file",
                    "method": "POST",
                    "complex": False,
                    "required_params": {
                        "path": "Full path (e.g., 'projects/MyProject/test.py')",
                        "content": "File content (string)"
                    },
                    "examples": [
                        "create file test.py",
                        "add file utils.py",
                        "write file main.py"
                    ],
                    "note": "Auto-prefixed with active project if relative path provided"
                },
                "update": {
                    "endpoint": "/update-file",
                    "method": "POST",
                    "complex": False,
                    "required_params": {
                        "path": "Full path (e.g., 'projects/MyProject/test.py')",
                        "content": "File content (string)"
                    },
                    "examples": [
                        "update file main.py",
                        "edit file utils.py",
                        "modify file config.json"
                    ],
                    "note": "Auto-prefixed with active project if relative path provided"
                },
                "delete": {
                    "endpoint": "/execute",
                    "method": "POST",
                    "complex": True,
                    "required_params": {
                        "task": "Deletion command (e.g., 'delete file test.py')"
                    },
                    "examples": [
                        "delete file test.py",
                        "remove file old.py",
                        "delete files test1.py test2.py"
                    ],
                    "note": "File deletion uses /execute endpoint. /update-file with empty content only clears/truncates file, does NOT delete it."
                }
            },
            "project_operations": {
                "create": {
                    "endpoint": "/projects/create/{name}",
                    "method": "POST",
                    "complex": False,
                    "required_params": {},
                    "examples": [
                        "create project MyApp",
                        "new project TestProject"
                    ]
                },
                "archive": {
                    "endpoint": "/projects/archive/{name}",
                    "method": "POST",
                    "complex": False,
                    "required_params": {},
                    "examples": [
                        "archive project OldProject",
                        "delete project TestProject"
                    ]
                },
                "list": {
                    "endpoint": "/projects/list",
                    "method": "GET",
                    "complex": False,
                    "required_params": {},
                    "examples": [
                        "list projects",
                        "show all projects"
                    ]
                },
                "set_active": {
                    "endpoint": "/projects/set-active/{name}",
                    "method": "POST",
                    "complex": False,
                    "required_params": {},
                    "examples": [
                        "set active project MyApp",
                        "switch to project TestProject"
                    ]
                }
            },
            "general_tasks": {
                "code_generation": {
                    "endpoint": "/execute",
                    "method": "POST",
                    "complex": True,
                    "required_params": {
                        "task": "Task description (string)"
                    },
                    "examples": [
                        "generate a new API endpoint",
                        "create a user authentication system",
                        "implement file upload functionality"
                    ],
                    "note": "Use for complex tasks requiring AI code generation"
                },
                "refactoring": {
                    "endpoint": "/execute",
                    "method": "POST",
                    "complex": True,
                    "required_params": {
                        "task": "Task description (string)"
                    },
                    "examples": [
                        "refactor the authentication system",
                        "improve error handling",
                        "optimize database queries"
                    ],
                    "note": "Use for code refactoring and improvements"
                }
            }
        },
        "error_handling": {
            "wrong_endpoint": {
                "status_code": 400,
                "error_type": "wrong_endpoint",
                "response_fields": {
                    "correct_endpoint": "POST /update-file",
                    "endpoint_url": "/update-file",
                    "required_parameters": "Object with parameter descriptions"
                },
                "action": "Retry request with correct endpoint"
            },
            "no_active_project": {
                "status_code": 400,
                "error_code": "NO_ACTIVE_PROJECT",
                "message": "You must set an active project before performing file operations",
                "action": "Call POST /projects/set-active/{name} first"
            },
            "path_outside_project": {
                "status_code": 400,
                "error_code": "PATH_OUTSIDE_PROJECT",
                "message": "File path must be within active project",
                "action": "Use path: projects/{active_project}/<file_path>"
            }
        },
        "best_practices": {
            "file_operations": [
                "Use /update-file for file create/update operations (with known content)",
                "Use /execute for file deletion operations",
                "Set active project before file operations",
                "Use full paths (projects/MyProject/file.py) or relative paths (file.py will be auto-prefixed)",
                "Note: /update-file with empty content only clears/truncates file, does NOT delete it"
            ],
            "complex_tasks": [
                "Use /execute for code generation, refactoring, multi-file changes",
                "Use /execute for AI-powered development tasks",
                "Do NOT use /execute for simple file operations"
            ],
            "project_management": [
                "Use direct project endpoints (/projects/*) for project operations",
                "Set active project after creation",
                "List projects to see available projects"
            ]
        }
    }
    
    return JSONResponse(routing_rules, status_code=200)


# ============================================================
#  📊 CONTEXT QUERY ENDPOINTS (TASK 8.8)
# ============================================================

@router.get("/context/snapshot")
async def get_snapshot(project: str = Query(None)):
    """
    Get project state snapshot.
    
    ✅ TASK 8.8: Snapshot query endpoint
    
    Args:
        project: Project name (optional, uses active project)
    
    Returns:
        Project state snapshot
    """
    try:
        from core.context_manager import context_manager
        from core.context_sync import get_project_state
        
        if not project:
            project = context_manager.get_project()
        
        if not project:
            return JSONResponse({
                "status": "error",
                "message": "No project specified and no active project set"
            }, status_code=400)
        
        snapshot = get_project_state(project)
        
        return JSONResponse({
            "status": "success",
            "snapshot": snapshot
        }, status_code=200)
        
    except Exception as e:
        log_message(f"[Context] Error getting snapshot: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.get("/context/events")
async def get_events(
    project: str = Query(None),
    event_type: str = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get event history for a project.
    
    ✅ TASK 8.8: Event query endpoint
    
    Args:
        project: Project name (optional, uses active project)
        event_type: Filter by event type (optional)
        limit: Maximum number of events
    
    Returns:
        Event history
    """
    try:
        from core.context_manager import context_manager
        from core.event_logger import read_events
        
        if not project:
            project = context_manager.get_project()
        
        if not project:
            return JSONResponse({
                "status": "error",
                "message": "No project specified and no active project set"
            }, status_code=400)
        
        events = read_events(project, event_type=event_type, limit=limit)
        
        return JSONResponse({
            "status": "success",
            "project": project,
            "events": events,
            "count": len(events)
        }, status_code=200)
        
    except Exception as e:
        log_message(f"[Context] Error getting events: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.get("/context/commits")
async def get_commits(project: str = Query(None), limit: int = Query(10, ge=1, le=100)):
    """
    Get commit reports for a project.
    
    ✅ TASK 8.8 ENHANCEMENT: Commit history query endpoint
    
    Args:
        project: Project name (optional, uses active project)
        limit: Maximum number of commits (default: 10, max: 100)
    
    Returns:
        Commit reports (most recent first)
    """
    try:
        from core.context_manager import context_manager
        from core.commit_tracker import load_commit_data
        
        if not project:
            project = context_manager.get_project()
        
        if not project:
            return JSONResponse({
                "status": "error",
                "error_code": "NO_ACTIVE_PROJECT",
                "message": "No project specified and no active project set"
            }, status_code=400)
        
        # Validate limit
        limit = min(max(1, limit), 100)  # Between 1 and 100
        
        # ✅ TASK 8.10.1: Load from unified commit_history.json
        commit_data = load_commit_data(project)
        last_commit = commit_data.get("last_commit")
        commit_history = commit_data.get("history", [])[:limit]
        
        return JSONResponse({
            "status": "success",
            "project": project,
            "commits": commit_history,
            "last_commit": last_commit,
            "max_commits": commit_data.get("max_commits", 3),
            "count": len(commit_history)
        }, status_code=200)
        
    except Exception as e:
        log_message(f"[Context] Error getting commits: {e}")
        return JSONResponse({
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": str(e)
        }, status_code=500)


@router.post("/context/sync")
async def sync_context_db(
    project: str = Query(None, description="Project name (optional, uses active project if not provided)"),
    force: bool = Query(False, description="Force full re-sync (ignores sync_metadata checks)")
) -> Dict[str, Any]:
    """
    Manually trigger sync of context_full.json and run_*.json to SQLite.
    
    ✅ TASK 8.11 COMPATIBILITY: Sync endpoint
    ✅ TASK 8.10.1.1 ALIGNMENT: Syncs from context_full.json (primary source)
    
    **Purpose:**
    Manually trigger synchronization of JSON files to SQLite database.
    Useful for:
    - Initial sync after TASK 8.11 implementation
    - Force re-sync after manual JSON edits
    - Recovery after database corruption
    
    **Syncs:**
    - context_full.json → SQLite (commits, snapshots, activity)
    - run_*.json → SQLite runs table (metadata only)
    - Checks sync_metadata for FIFO trim events (full re-sync if trimmed)
    
    **Query Parameters:**
    - project: Project name (optional, uses active project if not provided)
    - force: Force full re-sync (default: false, respects sync_metadata)
    
    **Returns:**
    - status: "success" or "error"
    - message: Status message
    - synced_files: List of synced files
    - sync_details: Detailed sync information
    
    **Example:**
    POST /context/sync?project=test_project&force=true
    """
    try:
        from core.context_manager import context_manager
        from core.context_indexer import (
            sync_context_full_to_sqlite,
            sync_run_logs_to_sqlite,
            init_context_db
        )
        
        # Get project name
        if not project:
            project = context_manager.get_project()
        
        if not project:
            return JSONResponse({
                "status": "error",
                "message": "No project specified and no active project set"
            }, status_code=400)
        
        # Validate project exists
        project_path = Path(f"projects/{project}")
        if not project_path.exists():
            return JSONResponse({
                "status": "error",
                "message": f"Project '{project}' not found"
            }, status_code=404)
        
        # Initialize database if needed
        if not init_context_db(project):
            return JSONResponse({
                "status": "error",
                "message": "Failed to initialize context database"
            }, status_code=500)
        
        synced_files = []
        sync_details = {}
        
        # Sync context_full.json
        if sync_context_full_to_sqlite(project, force=force):
            synced_files.append("context_full.json")
            sync_details["context_full"] = "synced"
        else:
            sync_details["context_full"] = "failed"
        
        # Sync run logs
        if sync_run_logs_to_sqlite(project, force=force):
            synced_files.append("run_*.json")
            sync_details["run_logs"] = "synced"
        else:
            sync_details["run_logs"] = "skipped or failed"
        
        return {
            "status": "success",
            "message": f"Sync completed for {project}",
            "project": project,
            "force": force,
            "synced_files": synced_files,
            "sync_details": sync_details
        }
        
    except Exception as e:
        log_message(f"[API] Error syncing context.db: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)
