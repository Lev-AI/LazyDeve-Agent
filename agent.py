from fastapi import FastAPI, Query, Body, Request, Depends, status
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List
import datetime
import asyncio
import aiohttp
import subprocess
import os
import sys
import json
import requests
import shutil
from datetime import datetime
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from core.basic_functional import read_file, update_file, log_message
from core.context_manager import get_context_summary
from core.custom_functional import rename_project
from core.config import PUBLIC_AGENT_URL
from core.llm_selector import get_llm_client, set_llm, get_provider_info
from core.lazydeve_boot import initializer
from core.event_bus import trigger_event
from core.auth_middleware import verify_token
from fastapi.responses import JSONResponse  
from fastapi.openapi.utils import get_openapi  

# Import Pydantic models from api/schemas
from api.schemas import CommitRequest, FormatCommitRequest, ExecBody

# Import utilities from utils modules
from utils.git_utils import (
    safe_git_command, safe_git_add, safe_git_commit, 
    safe_git_push, safe_git_pull, safe_git_status, safe_git_rm,
    remove_via_git, remove_via_git_multi
)
from utils.translation import configure_utf8, gpt_translate_to_english, translate_prompt
from utils.webhook import log_network_error, fetch_with_retry, safe_webhook_notify, handle_response
from utils.path_utils import (
    extract_path_from_text, extract_paths_from_text,
    load_restricted_directories, is_restricted_path, is_safe_path
)
from utils.startup import (
    load_agent_rules, sync_agent_memory, agent_intro,
    update_agent_state, notify_agent_ready
)

# Import API routers (Task 7 Phase 2 - Modular Architecture)
from api.routes.system import router as system_router
from api.routes.protection import router as protection_router
from api.routes.admin import router as admin_router
from api.routes.llm import router as llm_router
from api.routes.git import router as git_router
from api.routes.files import router as files_router
from api.routes.analysis import router as analysis_router
from api.routes.projects import router as projects_router
from api.routes.execute import router as execute_router
from api.routes.run_local import router as run_local_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup logic
    try:
        print("[Agent] Starting LazyDeve Agent initialization...")
        print(f"[Agent] Cloudflare tunnel active at {PUBLIC_AGENT_URL}")
        
        # Configure UTF-8 encoding for multilingual support
        configure_utf8()
        
        # ======================================================
        # ✅ TASK 3.5.1: Per-Project Auto-Commit System
        # ======================================================
        try:
            print("[Agent] 🔍 Checking root repository for changes...")
            status_result = safe_git_status()
            
            # Root-level auto-commit (keep existing behavior)
            if status_result["status"] == "success" and status_result["stdout"].strip():
                print("[Agent] Local root changes detected, auto-committing...")
                add_result = safe_git_add()
                if add_result["status"] == "success":
                    commit_result = safe_git_commit("[LazyDeve] auto: Startup commit (root)")
                    if commit_result["status"] == "success":
                        print(f"[Agent] ✅ Root auto-commit successful")
                        push_result = safe_git_push()
                        if push_result["status"] == "success":
                            print(f"[Agent] ✅ Root auto-push successful")
                        else:
                            print(f"[Agent] ⚠️ Root auto-push failed: {push_result.get('error', '')}")
                else:
                    print(f"[Agent] ⚠️ Root auto-add failed: {add_result.get('error', '')}")
            else:
                print("[Agent] No local root changes to commit")
            
            # ======================================================
            # 🔄 NEW: Per-Project Git Auto-Commit Logic
            # ======================================================
            projects_dir = "projects"
            if os.path.exists(projects_dir):
                # Get list of project directories
                project_dirs = [d for d in os.listdir(projects_dir) 
                                if os.path.isdir(os.path.join(projects_dir, d))]
                
                if not project_dirs:
                    print("[Agent] No projects found in /projects/")
                else:
                    print(f"[Agent] 🔍 Scanning {len(project_dirs)} project(s) for uncommitted changes...")
                    
                    for project_name in project_dirs:
                        project_path = os.path.join(projects_dir, project_name)
                        git_dir = os.path.join(project_path, ".git")
                        
                        if os.path.exists(git_dir):
                            print(f"[Agent] Checking {project_name}...")
                            
                            # ✅ TASK 4.2.3: Ensure GitHub remote exists before checking status
                            from utils.github_api import ensure_github_remote_exists
                            from core.config import allow_github_access
                            
                            if allow_github_access:
                                remote_result = ensure_github_remote_exists(project_name, project_path)
                                if remote_result["status"] == "created":
                                    print(f"[Agent] ✅ GitHub repo auto-created for {project_name}: {remote_result['repo_url']}")
                                elif remote_result["status"] == "linked":
                                    print(f"[Agent] ✅ GitHub repo linked for {project_name}: {remote_result['repo_url']}")
                                elif remote_result["status"] == "error":
                                    print(f"[Agent] ⚠️ GitHub repo creation failed for {project_name}: {remote_result.get('error', '')}")
                            
                            project_status = safe_git_status(cwd=project_path)
                            
                            if project_status["status"] == "success" and project_status["stdout"].strip():
                                print(f"[Agent] 🟡 Changes detected in {project_name}, auto-committing...")
                                add_result = safe_git_add(cwd=project_path)
                                
                                if add_result["status"] == "success":
                                    commit_result = safe_git_commit(
                                        f"[LazyDeve] auto: Startup commit ({project_name})",
                                        cwd=project_path
                                    )
                                    
                                    if commit_result["status"] == "success":
                                        print(f"[Agent] ✅ {project_name} committed successfully")
                                        
                                        # ✅ TASK 4.2 FIX: Only push if allow_github_access=true
                                        from core.config import allow_github_access
                                        if allow_github_access:
                                            push_result = safe_git_push(branch="main", cwd=project_path)
                                            
                                            if push_result["status"] == "success":
                                                print(f"[Agent] ✅ {project_name} pushed successfully")
                                            elif "no remote" in push_result.get("error", "").lower():
                                                print(f"[Agent] ⚠️ {project_name}: local commit only (no remote)")
                                            else:
                                                print(f"[Agent] ⚠️ {project_name}: push failed - {push_result.get('error', '')}")
                                        else:
                                            print(f"[Agent] ℹ️ {project_name}: local commit only (GitHub access disabled)")
                                    else:
                                        print(f"[Agent] ⚠️ Commit failed for {project_name}: {commit_result.get('error', '')}")
                                else:
                                    print(f"[Agent] ⚠️ Add failed for {project_name}: {add_result.get('error', '')}")
                            else:
                                print(f"[Agent] ✅ No changes in {project_name}")
                        else:
                            print(f"[Agent] ⚠️ {project_name}: No .git directory (skipping)")
            else:
                print("[Agent] No /projects/ directory found")
            
            print("[Agent] 🧩 Auto-commit cycle completed for all repositories.")
        
        except Exception as e:
            print(f"[Agent] ⚠️ Per-project auto-commit failed: {e}")
            import traceback
            print(f"[Agent] Traceback: {traceback.format_exc()}")
        
        # Post-run consistency check
        try:
            from core.basic_functional import post_run_consistency_check
            post_run_consistency_check()
        except ImportError:
            print("[Agent] Post-run consistency check failed: cannot import name 'post_run_consistency_check' from 'core.basic_functional'")
        except Exception as e:
            print(f"[Agent] Post-run consistency check failed: {e}")
        
        print("[Agent] Auto-commit cycle completed.")
        
        # ✅ TASK 4: Restore last active project on startup
        try:
            from core.context_manager import context_manager, restore_last_active_project
            from core.basic_functional import log_message
            
            restored_project = restore_last_active_project()
            
            if restored_project:
                log_message(f"[Startup] ✅ Restored active project: {restored_project}")
                log_message(f"[Startup] Project context and memory loaded")
                print(f"[Agent] ✅ Restored active project: {restored_project}")
            else:
                log_message("[Startup] ⚠️ No active project restored - user must set one")
                log_message("[Startup] Protection system will block /execute until project is set")
                print("[Agent] ⚠️ No active project restored - user must set one via /projects/set-active/{name}")
        except Exception as restore_error:
            log_message(f"[Startup] Error restoring last active project: {restore_error}")
            print(f"[Agent] ⚠️ Could not restore last active project: {restore_error}")
        
        # ✅ TASK 8.9: Initialize context on startup
        try:
            from core.context_initializer import initialize_context_on_start
            if restored_project:
                init_result = initialize_context_on_start(restored_project)
                if init_result:
                    log_message(f"[Startup] ✅ Context initialized for {restored_project}")
                else:
                    log_message(f"[Startup] ⚠️ Context initialization returned None for {restored_project}")
        except Exception as init_error:
            log_message(f"[Startup] ⚠️ Context initialization failed: {init_error}")
        
        # ✅ TASK 8.10: Self-Trigger FIFO Cleanup - Check .aider.chat.history.md on startup
        # (Aider writes this file directly, so we check it at startup)
        try:
            from core.file_maintenance import trim_aider_history, MAX_AIDER_HISTORY_SIZE_MB
            aider_file = ".aider.chat.history.md"
            if os.path.exists(aider_file):
                size_mb = os.path.getsize(aider_file) / (1024 * 1024)
                if size_mb > MAX_AIDER_HISTORY_SIZE_MB:
                    log_message(f"[Startup] 🧹 Trimming .aider.chat.history.md ({size_mb:.2f}MB > {MAX_AIDER_HISTORY_SIZE_MB}MB)")
                    trim_aider_history(aider_file, MAX_AIDER_HISTORY_SIZE_MB)
        except Exception as e:
            log_message(f"[Startup] ⚠️ Aider history check failed: {e}")
        
        # ✅ TASK 8.10: Self-Trigger FIFO Cleanup - Check log files in logs/ directory on startup
        # (Log files are written by logging module directly, not through safe_append_log)
        try:
            from core.file_maintenance import maintain_logs_directory, MAX_LOG_SIZE_MB
            logs_dir = "logs"
            if os.path.exists(logs_dir):
                trimmed_count = maintain_logs_directory(logs_dir, MAX_LOG_SIZE_MB)
                if trimmed_count > 0:
                    log_message(f"[Startup] 🧹 Trimmed {trimmed_count} log file(s) in {logs_dir}")
        except Exception as e:
            log_message(f"[Startup] ⚠️ Log files check failed: {e}")
        
        # Initialize agent
        print("[Agent] Initialization completed successfully")
        print("=" * 70)
        print("🤖 LazyDeve Agent – Initialization Report (v1.4.1)")
        print("=" * 70)
        print("Hello, I am LazyDeve — your autonomous development agent. I self-update on every launch, sync with GitHub, and maintain local projects in full parity. You can interact with me via /execute or /ping-agent.")
        
        # Display capabilities
        print("📘 Active Capabilities:")
        capabilities = [
            "auto_commit", "auto_push", "auto_sync", "context_awareness",
            "allow_github_access", "allow_webhook_notify", "project_memory_sync",
            "intro_message_enabled", "post_update_summary", "post_update_notifier",
            "auto_state_refresh"
        ]
        for cap in capabilities:
            print(f"   - {cap}: ✅ Enabled")
        
        # Display endpoints
        print("🔧 Available Endpoints:")
        endpoints = [
            ("/ping-agent", "check agent status"),
            ("/execute", "run AI-assisted tasks"),
            ("/status", "get Git repository status and agent freshness"),
            ("/commits", "retrieve recent Git commit history"),
            ("/list-files", "get recursive project file listing"),
            ("/set-llm", "switch LLM provider (OpenAI, Anthropic, Gemini, Mistral)"),
            ("/llm-info", "get current LLM provider information"),
            ("/sync", "pull updates from GitHub"),
            ("/logs", "view recent activity"),
            ("/read-file", "read file contents"),
            ("/update-file", "update file contents"),
            ("/commit", "commit changes"),
            ("/format-commit", "format commit messages"),
            ("/rename-project", "rename project"),
            ("/ping-memory", "check memory sync status"),
            ("/analyze-code", "perform AI-assisted or static code analysis"),
            ("/run-tests", "execute unit/integration tests"),
            ("/openapi.yaml", "get API schema for ChatGPT Apps"),
            ("/protection-status", "get system protection status"),
            ("/check-protection", "check file operation protection"),
            ("/projects/list", "list all projects"),
            ("/projects/create/{name}", "create new project"),
            ("/projects/active", "get active project"),
            ("/projects/set-active/{name}", "set active project"),
            ("/projects/info/{name}", "get project information"),
            ("/projects/commit", "commit project changes"),
            # ✅ TASK 8.8.1: Context endpoints (Task 8.8)
            ("/context/snapshot", "get project state snapshot"),
            ("/context/events", "query event history"),
            ("/context/commits", "get commit reports and history"),
            ("/admin/reset-init", "reset initialization state (admin)")
        ]
        for endpoint, description in endpoints:
            print(f"  • {endpoint:<20} → {description}")
        
        # Memory sync status
        log_message("✅ Agent memory synced and ready.")
        print("=" * 70)
        print("=" * 70)
        
    except Exception as e:
        print(f"[Agent] Startup failed: {e}")
    
    yield  # App is running
    
    # Shutdown logic (if needed)
    print("[Agent] Shutting down...")

app = FastAPI(
    title="LazyDeve Agent",
    description="Local Aider-based development agent.",
    version="1.3.0",  # Updated version number
    servers=[{"url": PUBLIC_AGENT_URL}],
    lifespan=lifespan
)

# ===============================
# Task 7 Phase 2 & Task 8: Register API Routes
# ===============================

# Task 7 Phase 2: Core endpoint routers (refactored from agent.py)
app.include_router(execute_router)      # /execute endpoint with HELPER 1 & 3
app.include_router(projects_router)     # /projects/* endpoints
app.include_router(files_router)        # /read-file, /update-file, /list-files
app.include_router(analysis_router)     # /analyze-code, /run-tests
app.include_router(run_local_router)   # ✅ TASK 8.7: /run-local
app.include_router(git_router)          # /commit, /sync, /commits, /status
app.include_router(llm_router)          # /set-llm, /llm-info
app.include_router(system_router)       # /ping-agent, /logs, /ping-memory, /openapi.yaml
app.include_router(protection_router)   # /protection-status, /check-protection
app.include_router(admin_router)        # /admin/reset-init

log_message("[Agent] Task 7 Phase 2 routers registered: execute, projects, files, analysis, git, llm, system, protection, admin")

# Task 8 Phase 4: Advanced feature routers (CPL, RAG, MCP)
try:
    from api.routes import memory, docs, context  # ✅ TASK 8.9.1: Add context router
    
    # Register routers with /api/v1 prefix (already in router definitions)
    app.include_router(memory.router)
    app.include_router(docs.router)
    app.include_router(context.router)  # ✅ TASK 8.9.1: Register context router
    
    log_message("[Agent] Task 8 API routes registered successfully (memory, docs, context)")
except ImportError as e:
    log_message(f"[Agent] Task 8 routes not available: {str(e)}")
except Exception as e:
    log_message(f"[Agent] ERROR: Error registering Task 8 routes: {str(e)}")

# ===============================
# ✅ TASK 6: Server-Side Auto-Initialization at Startup
# ===============================

@app.on_event("startup")
async def startup_initialization():
    """
    Run full initialization sequence after server is ready.
    This ensures agent is ready even if ChatGPT doesn't load schema.
    
    Note: @app.on_event("startup") is deprecated in FastAPI 0.93+ but still works.
    Future migration: Consider using background task in lifespan context manager.
    """
    # Brief delay to ensure server is fully ready
    import asyncio
    await asyncio.sleep(0.5)
    
    try:
        from core.lazydeve_boot import initializer
        from core.basic_functional import log_message
        
        log_message("[Startup] 🚀 Starting server-side auto-initialization...")
        print("[Agent] 🚀 Running full initialization sequence at startup...")
        
        # Run full initialization sequence (calls all 6 endpoints from boot_sequence)
        # This validates: /ping-agent, /status, /commits, /logs, /projects/list, /projects/active
        init_result = await initializer.run_initialization()
        
        if init_result.get("status") in ["success", "already_initialized"]:
            log_message("[Startup] ✅ Server-side initialization completed successfully")
            print("🤖 LazyDeve auto-initialization completed successfully")
            
            # Log summary of boot results
            if "results" in init_result:
                results = init_result["results"]
                successful = sum(1 for r in results.values() if r.get("success"))
                total = len(results)
                log_message(f"[Startup] Initialization: {successful}/{total} endpoints verified")
                print(f"[Agent] Initialization: {successful}/{total} endpoints verified")
        else:
            log_message(f"[Startup] ⚠️ Initialization completed with status: {init_result.get('status')}")
            print(f"⚠️ Initialization status: {init_result.get('status')}")
            # Don't fail - middleware will retry on first request
            
    except Exception as e:
        log_message(f"[Startup] ⚠️ Server-side initialization failed: {e}")
        print(f"⚠️ Server-side initialization failed: {e}")
        # Don't fail startup - middleware will handle initialization on first request
        import traceback
        log_message(f"[Startup] Traceback: {traceback.format_exc()}")

# ===============================
# Auto-Initialization Middleware
# ===============================

@app.middleware("http")
async def autoinit_middleware(request: Request, call_next):
    """
    Auto-initialization middleware.
    Runs initialization on first HTTP request, then passes through.
    """
    if not initializer.is_initialized() and request.url.path not in ["/docs", "/openapi.json", "/redoc"]:
        try:
            log_message("[Middleware] First request detected, running initialization...")
            init_result = await initializer.run_initialization()
            log_message(f"[Middleware] Initialization result: {init_result.get('status', 'unknown')}")
        except Exception as e:
            # Log error but don't block requests
            log_message(f"[Middleware] Initialization failed: {e}")
    
    response = await call_next(request)
    return response

# ===============================
# Translation & UTF-8 utilities now in utils/translation.py
# Git operations now in utils/git_utils.py
# Webhook operations now in utils/webhook.py
# Path utilities now in utils/path_utils.py
# ===============================

# ===============================
# Agent Initialization & GitHub Sync
# ===============================
# Helper functions moved to utils/startup.py, utils/webhook.py, utils/path_utils.py (Task 7 Phase 3)
    """
    Log network errors to both console and dedicated log file.
    Provides structured error information for debugging.
    """
@app.post("/format-commit")
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


@app.post("/rename-project")
def rename(src: str = Body(...), dst: str = Body(...)):
    return rename_project(src, dst)

# ============================================================
#  🔍 ANALYZE-CODE ENDPOINT (SAFE + ASYNC)
# ============================================================

# ============================================================
#  🧪 RUN-TESTS ENDPOINT (ASYNC + SECURE)
# ============================================================

# ===============================
# Project Management Endpoints
# ===============================

from fastapi import APIRouter
from core import project_manager as pm

# ===============================
# Admin Endpoints
# ===============================

# ===============================
# Startup Sequence
# ===============================

if __name__ == "__main__":
    # Configure UTF-8 for all output
    configure_utf8()
    
    # Load environment variables
    load_dotenv()
    
    # Display startup message
    print("[Agent] Initializing LazyDeve Agent...")
    log_message("[Agent] Starting LazyDeve Agent initialization")
    
    # Run agent intro and memory sync
    agent_intro()
    
    # Update agent state
    update_agent_state("ready")
    
    # Notify agent ready
    notify_agent_ready()
    
    print("[Agent] Initialization completed successfully")
    print("[Agent] Server ready to accept requests")
