"""
Execute Route - Core /execute endpoint with AI task execution
Extracted from agent.py for Task 7 Phase 2

✅ TASK 8: Now uses Command Precision Layer (CPL) for deterministic routing
- Centralized command parsing in core/command_parser.py
- HELPER 1 & 3 consolidated into CPL
"""

import re
import time  # ✅ TASK 8.11.1: For execution time tracking
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from core.auth_middleware import verify_token
from core.basic_functional import log_message
from core.event_bus import trigger_event
from utils.path_utils import extract_path_from_text, extract_paths_from_text
from utils.git_utils import remove_via_git, remove_via_git_multi
from utils.translation import translate_prompt
from core.command_parser import parse_command, log_parsed_command, inject_project_path

router = APIRouter()


@router.post("/execute", dependencies=[Depends(verify_token)])
async def execute_task_endpoint(request: Request):
    """
    Execute AI-assisted development tasks via Aider CLI.
    
    AI-powered operations: refactoring, code generation, deletions, and complex multi-file edits.
    
    📌 DECISION RULE:
    - If you already know the exact file content → use /update-file  
    - If you need AI to generate, refactor, or modify code → use /execute
    
    ⚠️ FILE PROTECTION:
    - Explicit commands like "create file X" are automatically redirected to /update-file  
    - Aider may still create files as part of AI-generated tasks (this is allowed)
    - Explicit natural-language edit commands targeting exact file content (e.g., "update file X with Y") redirect to /update-file
    
    📌 USE /execute FOR:
    - Refactoring or improving existing code  
    - Generating new modules or features  
    - Deleting one or more files  
    - Coordinated multi-file changes
    
    📌 USE /update-file FOR:
    - Creating a file when you already have its full content  
    - Replacing file text directly (no AI reasoning)
    
    ⚠️ REQUIREMENTS:
    - Active project must be set (returns 400 if not)
    - "task" field is REQUIRED (or use "prompt"/"instruction" as aliases)
    - All changes are automatically committed after execution
    
    📦 FORMAT: {"task": "description"}  
    Optional fields: files, project, model.
    
    🧪 EXAMPLES:
    - {"task": "Refactor authentication to use JWT"}  
    - {"task": "Add logging to all API endpoints"}  
    - {"task": "Delete old_config.py"}  
    - {"task": "Generate a new API endpoint", "files": ["routes/users.py"]}
    
    Args:
        task/prompt/instruction: Task description (REQUIRED - use "task" field)
        project: Project name (OPTIONAL - uses active project if not provided)
        model: LLM model (OPTIONAL - auto-selected if not provided)
        files: List of files to include in Aider context (OPTIONAL)
        commit: Auto-commit flag (OPTIONAL - currently not implemented, changes always committed)
    
    Returns:
        Task execution result with status
        
    Error Responses:
        - 400: Invalid task, wrong endpoint for action, or file operation detected (redirects to /update-file)
        - 400: NO_ACTIVE_PROJECT - No active project set
    """
    from core.basic_functional import run_aider_task_async

    try:
        data = await request.json()

        # Accept multiple formats (task, prompt, or instruction)
        task = data.get("task") or data.get("prompt") or data.get("instruction")
        commit = data.get("commit", True)
        files = data.get("files", [])
        project = data.get("project")
        
        # Get active project from context manager
        # 🔒 TASK 1 FIX: Remove "LazyDeve" fallback - let protection system handle None
        from core.context_manager import context_manager
        active_project = project or context_manager.get_project()
        
        # Dynamic LLM selection (Task 7.7.14)
        # If user explicitly provides a model, use it; otherwise auto-select
        user_provided_model = data.get("model")
        if user_provided_model:
            model = user_provided_model
            log_message(f"[Agent] /execute → task={task[:50]}, model={model} (user-specified)")
        else:
            # Auto-select model based on task type and context
            from core.llm_selector import get_llm_selector
            llm_selector = get_llm_selector()
            selected_model = llm_selector.select_model(task, active_project)
            model = selected_model
            log_message(f"[Agent] /execute → task={task[:50]}, model={model} (auto-selected for project={active_project})")

        if not task or task.strip() == "":
            return JSONResponse(
                {"status": "error", "message": "Empty task/prompt/instruction"},
                status_code=400
            )

        # ✅ TASK 8: Command Precision Layer - Parse command intent EARLY
        # This replaces HELPER 1 and HELPER 3 with centralized, deterministic parsing
        cpl_result = parse_command(task)
        log_parsed_command(cpl_result)
        
        intent = cpl_result.get("intent")
        params = cpl_result.get("params", {})
        confidence = cpl_result.get("confidence", 0.0)
        
        log_message(f"[CPL] Intent: {intent}, Confidence: {confidence:.2f}, Params: {params}")
        
        # ============================================================
        # CPL INTENT ROUTING (replaces HELPER 3 - Archive Detection)
        # ============================================================
        if intent == "archive_project":
            project_name = params.get("project_name")
            
            if not project_name:
                log_message(f"[CPL] Could not extract project name from: {task[:100]}")
                return JSONResponse({
                    "status": "error",
                    "error_type": "invalid_request",
                    "message": "Could not extract project name from archive command",
                    "suggestion": "Please specify project name: 'archive project ProjectName'",
                    "task_received": task[:100]
                }, status_code=400)
            
            # Execute archive directly
            from core.project_manager import archive_project
            
            log_message(f"[CPL] Executing archive_project('{project_name}')...")
            try:
                result = archive_project(project_name)
                log_message(f"[CPL] archive_project() returned: status={result.get('status')}, error_code={result.get('error_code', 'N/A')}")
                
                if result.get("status") == "archived":
                    log_message(f"[CPL] ✅ Project archived successfully: {project_name}")
                    
                    # Build response
                    response_data = {
                        "status": "success",
                        "operation": "archive_project",
                        "result": result,
                        "message": result.get("message", f"Project '{project_name}' archived successfully"),
                        "task_received": task[:100]
                    }
                    
                    # Handle project selection requirement
                    if result.get("requires_project_selection"):
                        from core.project_manager import list_projects
                        available_projects = list_projects()
                        response_data["requires_project_selection"] = True
                        response_data["available_projects"] = available_projects
                        response_data["suggestion"] = "Use POST /projects/set-active/{name} to select a new active project"
                    
                    return JSONResponse(response_data, status_code=200)
                else:
                    # Archive failed
                    error_code = result.get("error_code", "UNKNOWN_ERROR")
                    status_code = 400 if error_code in ["ACTIVE_PROJECT", "INVALID_NAME"] else 404
                    log_message(f"[CPL] ❌ Archive failed: {result.get('message', 'Unknown error')} (error_code: {error_code})")
                    return JSONResponse({
                        "status": "error",
                        "operation": "archive_project",
                        "error_type": error_code,
                        "message": result.get("message", "Archive operation failed"),
                        "result": result,
                        "task_received": task[:100]
                    }, status_code=status_code)
                    
            except Exception as e:
                log_message(f"[CPL] ❌ Exception during archive: {type(e).__name__}: {e}")
                import traceback
                log_message(f"[CPL] 🔍 Traceback: {traceback.format_exc()}")
                return JSONResponse({
                    "status": "error",
                    "error_type": "archive_exception",
                    "message": f"Archive operation failed: {str(e)}",
                    "task_received": task[:100]
                }, status_code=500)
        
        # ============================================================
        # CPL INTENT ROUTING - Create Project (DEPRECATED - TASK 8.2)
        # ============================================================
        # ❌ REMOVED: ChatGPT should use POST /projects/create/{name} directly
        # This routing has been deprecated because:
        #   1. CPL no longer detects create_project intent (Task 8.2 minimization)
        #   2. ChatGPT should naturally use direct endpoint via OpenAPI schema
        #   3. This code path is now unreachable
        # Original code preserved for reference (Task 8):
        # elif intent == "create_project":
        #     return JSONResponse({"error": "wrong_endpoint", "suggestion": "Use POST /projects/create/{name}"})
        # ============================================================
        
        # ============================================================
        # CPL INTENT ROUTING - Commit Changes (DEPRECATED - TASK 8.2)
        # ============================================================
        # ❌ REMOVED: ChatGPT should use POST /commit directly
        # This routing has been deprecated because:
        #   1. CPL no longer detects commit_changes intent (Task 8.2 minimization)
        #   2. ChatGPT should naturally use direct endpoint via OpenAPI schema
        #   3. This code path is now unreachable
        # Original code preserved for reference (Task 8):
        # elif intent == "commit_changes":
        #     return JSONResponse({"error": "wrong_endpoint", "suggestion": "Use POST /commit"})
        # ============================================================
        
        # ============================================================
        # CPL INTENT ROUTING - Update/Create File (TASK 8.4 - SECURITY FIX)
        # ============================================================
        elif intent == "update_file":
            file_path = params.get("file_path")
            content = params.get("content")
            
            # ✅ TASK 8.4 SECURITY: Don't execute file operations in /execute
            # Return structured error response guiding to correct endpoint
            log_message(f"[CPL] ⚠️ SECURITY: File operation detected in /execute - redirecting to /update-file")
            log_message(f"[CPL] File operation attempt: file_path={file_path}, has_content={content is not None}")
            
            # Security audit log
            log_message(f"[SECURITY] File operation blocked in /execute - endpoint isolation enforced")
            
            return JSONResponse({
                "status": "error",
                "error_type": "wrong_endpoint",
                "message": "File creation/update operations must use POST /update-file endpoint",
                "suggestion": "Use POST /update-file with file_path and content parameters. For file deletion, use POST /execute with task='delete file <path>'",
                "detected_intent": "update_file",
                "file_path": file_path,
                "correct_endpoint": "POST /update-file",
                "endpoint_url": "/update-file",
                "required_parameters": {
                    "file_path": "Full path to file (e.g., 'projects/MyProject/test.py')",
                    "content": "File content (string)"
                },
                "note": "This redirect is for file creation/update only. File deletion should use /execute endpoint.",
                "task_received": task[:100]
            }, status_code=400)
        
        # ============================================================
        # CPL INTENT ROUTING - Delete File (RESTORED - Original Behavior)
        # ✅ TASK 3.6.2: Restore endpoint separation - /execute handles deletions
        # ============================================================
        elif intent == "delete_file":
            file_path = params.get("file_path")
            
            if not file_path:
                log_message(f"[CPL] Could not extract file path from: {task[:100]}")
                return JSONResponse({
                    "status": "error",
                    "error_type": "invalid_request",
                    "message": "Could not extract file path from deletion command",
                    "suggestion": "Please specify file path: 'delete file test.py'",
                    "task_received": task[:100]
                }, status_code=400)
            
            # ✅ TASK 6.2: Support both single file (string) and multi-file (list)
            is_multi_file = isinstance(file_path, list)
            
            if is_multi_file:
                log_message(f"[CPL] 🗑️ Multi-file deletion detected: {len(file_path)} file(s)")
                paths = file_path  # Already a list
            else:
                log_message(f"[CPL] 🗑️ Single-file deletion: {file_path}")
                paths = [file_path]  # Convert to list for unified handling
            
            # ✅ TASK 6.2: Extract project path from first path (all paths should be in same project)
            first_path_normalized = paths[0].replace("\\", "/")
            project_match = re.search(r'projects/([^/]+)', first_path_normalized)
            
            if project_match:
                project_path = f"projects/{project_match.group(1)}"
                project = project_match.group(1)
            else:
                # Fallback: get from context manager
                from core.context_manager import context_manager
                project = context_manager.get_project()
                project_path = None
            
            # ✅ TASK 6.2: Use appropriate deletion function
            if len(paths) == 1:
                # Single file deletion
                deletion_result = remove_via_git(paths[0], cwd=project_path) if project_path else remove_via_git(paths[0])
            else:
                # Multi-file deletion
                deletion_result = remove_via_git_multi(paths, cwd=project_path) if project_path else remove_via_git_multi(paths)
            
            if deletion_result.get("status") == "success":
                log_message(f"[CPL] ✅ File deletion successful: {len(paths)} file(s)")
                return JSONResponse({
                    "status": "success",
                    "result": deletion_result,
                    "project": project,
                    "commit": commit,  # Note: commit is already in scope from line 81
                    "operation": "git_deletion",
                    "detected_intent": "delete_file",
                    "file_path": file_path,  # Preserve original (string or list)
                    "deleted_count": len(paths) if is_multi_file else 1
                }, status_code=200)
            else:
                log_message(f"[CPL] ❌ File deletion failed: {deletion_result.get('message', 'Unknown error')}")
                return JSONResponse({
                    "status": "error",
                    "result": deletion_result,
                    "project": project,
                    "operation": "git_deletion",
                    "detected_intent": "delete_file",
                    "file_path": file_path,
                    "deleted_count": 0
                }, status_code=500)
        
        # ============================================================
        # CPL INTENT ROUTING - Run Local Script (TASK 8.7.1 - OPTION A)
        # ============================================================
        elif intent == "run_local":
            script_path = params.get("script_path")
            
            if not script_path:
                log_message(f"[CPL] Could not extract script path from: {task[:100]}")
                return JSONResponse({
                    "status": "error",
                    "error_type": "invalid_request",
                    "message": "Could not extract script path from command",
                    "suggestion": "Please specify script path: 'run script.py' or 'execute file.py'",
                    "task_received": task[:100]
                }, status_code=400)
            
            # ✅ OPTION A: Internal delegation - call shared core function
            # Similar to archive_project pattern, but using extracted core logic
            log_message(f"[CPL] ✅ Script execution detected in /execute - using internal delegation")
            log_message(f"[CPL] Script execution: script_path={script_path}")
            
            from core.context_manager import context_manager
            from api.routes.run_local import execute_script_core
            
            active_project = context_manager.get_project()
            if not active_project:
                return JSONResponse({
                    "status": "error",
                    "error_type": "invalid_request",
                    "message": "No active project set. Use /projects/set-active/{name} first",
                    "task_received": task[:100]
                }, status_code=400)
            
            # Extract optional args and timeout from params if available
            args = params.get("args", [])
            timeout = params.get("timeout", 60)
            
            try:
                timeout = int(timeout)
            except (ValueError, TypeError):
                timeout = 60
            
            # Call shared core function
            result = await execute_script_core(
                script_path=script_path,
                active_project=active_project,
                args=args,
                timeout=timeout
            )
            
            # Convert result dict to JSONResponse with appropriate status code
            status_code = 200
            if result.get("status") == "error":
                # Map error codes to HTTP status codes
                error_code = result.get("error_code", "INTERNAL_ERROR")
                if error_code == "PROJECT_NOT_FOUND":
                    status_code = 404
                elif error_code == "PATH_VIOLATION":
                    status_code = 403
                elif error_code == "SCRIPT_NOT_FOUND":
                    status_code = 404
                elif error_code == "RUN_TIMEOUT":
                    status_code = 504
                elif error_code == "INTERPRETER_NOT_FOUND":
                    status_code = 503
                elif error_code in ["MISSING_PARAMETER", "INVALID_EXTENSION", "EXECUTION_NOT_CONFIGURED"]:
                    status_code = 400
                else:
                    status_code = 500
            
            log_message(f"[CPL] ✅ Script execution completed: status={result.get('status')}, returncode={result.get('returncode')}")
            
            return JSONResponse(result, status_code=status_code)
        
        # ✅ For all other intents (including execute_aider), continue with normal flow
        # This preserves existing functionality for translation, Aider execution, etc.
        
        # ✅ TASK 8: Old HELPER 3 removed - now handled by CPL above

        # GPT Translation Layer - Translate non-English prompts to English
        original_task = task
        task = translate_prompt(task)
        if task != original_task:
            log_message(f"[Agent] 🔄 Task translated: '{original_task}' → '{task}'")

        # Built-in connection test
        if task == "check connection and return ok":
            return JSONResponse({"status": "success", "message": "ok"}, status_code=200)

        # ✅ TASK 8: Old HELPER 1 & 2 removed - now handled by CPL above

        # Git-driven deletion detection (supports multi-file and multilingual)
        # NOTE: This is CORRECT usage of /execute - deletion belongs here!
        deletion_keywords = ["delete", "удали", "remove", "удалить", "מחק", "حذف", "删除", "削除"]
        if any(keyword in task.lower() for keyword in deletion_keywords):
            log_message(f"[Agent] 🗑️ Deletion command detected: {task}")
            
            # Try multi-file extraction first (supports multiple files)
            paths = extract_paths_from_text(task)
            
            # ✅ BUG FIX (Task 8.8.2 Bug #3): Inject project paths to prevent project deletion
            # This ensures all deletion paths are scoped to the active project
            if paths:
                paths = [inject_project_path(p) for p in paths]
            
            # If multi-file extraction found multiple files, use multi-file deletion
            if len(paths) > 1:
                log_message(f"[Agent] 🗑️ Multi-file deletion detected: {len(paths)} files")
                # ✅ TASK 3.6.1: Extract project path and pass as cwd
                # ✅ CRITICAL FIX: Normalize path (Windows backslashes → forward slashes) before regex
                first_path_normalized = (paths[0] if paths else "").replace("\\", "/")
                project_match = re.search(r'projects/([^/]+)', first_path_normalized)
                if project_match:
                    project_path = f"projects/{project_match.group(1)}"
                    deletion_result = remove_via_git_multi(paths, cwd=project_path)
                else:
                    # Fallback to current behavior if path doesn't match project pattern
                    deletion_result = remove_via_git_multi(paths)
                
                return JSONResponse({
                    "status": deletion_result["status"],
                    "result": deletion_result,
                    "project": project,
                    "commit": commit,
                    "operation": "git_multi_deletion",
                    "files_deleted": len(deletion_result.get("deleted", [])),
                    "files_skipped": len(deletion_result.get("skipped", [])),
                    "files_failed": len(deletion_result.get("failed", []))
                }, status_code=200 if deletion_result["status"] == "success" else 500)
            
            # If multi-file extraction found one file, or fallback to single-file extraction
            elif len(paths) == 1:
                path = paths[0]
            else:
                # Fallback to original single-file extraction
                path = extract_path_from_text(task)
                # ✅ BUG FIX (Task 8.8.2 Bug #3): Inject project path for single-file deletion
                if path:
                    path = inject_project_path(path)
            
            if not path and len(paths) == 0:
                error_msg = "❌ Could not extract file/folder path from deletion command"
                log_message(f"[Agent] {error_msg}")
                return JSONResponse(
                    {"status": "error", "message": error_msg, "suggestion": "Try: 'delete file.txt' or 'удали папку'"},
                    status_code=400
                )
            
            # ✅ TASK 3.6.1: Perform single-file Git-driven deletion with project context
            # Extract project path and pass as cwd
            # ✅ CRITICAL FIX: Normalize path (Windows backslashes → forward slashes) before regex
            normalized_path = path.replace("\\", "/")
            project_match = re.search(r'projects/([^/]+)', normalized_path)
            if project_match:
                project_path = f"projects/{project_match.group(1)}"
                deletion_result = remove_via_git(path, cwd=project_path)
            else:
                # Fallback to current behavior if path doesn't match project pattern
                deletion_result = remove_via_git(path)
            
            if deletion_result["status"] == "success":
                return JSONResponse({
                    "status": "success",
                    "result": deletion_result,
                    "project": project,
                    "commit": commit,
                    "operation": "git_deletion"
                }, status_code=200)
            else:
                return JSONResponse({
                    "status": "error",
                    "result": deletion_result,
                    "project": project,
                    "operation": "git_deletion"
                }, status_code=500)

        # Perform the Aider task asynchronously
        # ✅ Task 5: Guard at Aider call site - prevent archive/delete from reaching Aider
        # This is a safety net in case HELPER 3 somehow didn't catch it
        task_lower_check = task.lower()
        if "archive" in task_lower_check or ("delete" in task_lower_check and "project" in task_lower_check):
            log_message(f"[Agent] ⚠️ Archive/delete command reached Aider call - this should not happen!")
            return JSONResponse({
                "status": "error",
                "error_type": "wrong_endpoint",
                "message": "Archive/delete commands should be handled by HELPER 3, not Aider",
                "suggestion": "Use POST /projects/archive/{name} endpoint instead",
                "task_received": task[:100]
            }, status_code=400)
        
        # Track execution time for run logging
        execution_start = time.time()
        
        result = await run_aider_task_async(task, model, files, project=active_project)
        
        execution_runtime = time.time() - execution_start
        
        # ✅ TASK 8.11.1: Log execution to run_*.json (for SQLite indexing)
        try:
            from core.logs.run_logger import log_run_execution
            
            # Determine status from result
            run_status = "success" if result.get("status") == "success" and result.get("returncode") == 0 else "failed"
            
            # Log execution (creates run_*.json file and indexes to SQLite)
            log_run_execution(
                project=active_project,
                script_path=f"aider_task: {task[:50]}",  # Use task as script identifier
                status=run_status,
                returncode=result.get("returncode", -1),
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                runtime=execution_runtime,
                args=files or [],
                task_context=task[:200]  # Truncate task for context
            )
        except Exception as log_error:
            # Don't fail the request if logging fails
            log_message(f"[Execute] ⚠️ Failed to log execution: {log_error}")

        # Memory Hooks Integration (Task 7.7.3b)
        # ✅ TASK 8.11.1: update_memory() moved to log_run_execution() above
        # Keep log_project_action() for plaintext logging (actions.log)
        if result.get("status") == "success":
            try:
                from core.memory_utils import log_project_action
                log_project_action(active_project, "execute", f"Task executed successfully: {task[:80]}")
            except Exception as memory_error:
                log_message(f"[Memory Hooks] Error: {memory_error}")

        # Trigger post-action event hooks
        trigger_event(
            "post_action",
            async_mode=True,
            project=project,
            action="execute",
            details=task[:100],  # Truncate for brevity
            success=result.get("status") == "success",
            model=model,
            commit=commit
        )
        trigger_event("post_execute", async_mode=True, project=project, task=task, result=result)

        return JSONResponse({
            "status": "success",
            "result": result,
            "project": project,
            "commit": commit
        }, status_code=200)

    except Exception as e:
        log_message(f"[Agent] /execute error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )

