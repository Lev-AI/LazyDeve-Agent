"""
Run Local Route - Execute project scripts in multiple languages
✅ TASK 8.7: Universal script execution endpoint
✅ ENHANCEMENT: Async-safe recursion protection with contextvars
"""

import os
import json
import shutil
import asyncio
import contextvars
from datetime import datetime
from typing import Set
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from core.auth_middleware import verify_token
from core.basic_functional import log_message
from core.context_manager import context_manager
from core.event_bus import trigger_event
from core.memory_utils import update_memory

router = APIRouter()

# ✅ ENHANCEMENT: Async-safe execution stack tracking using contextvars
# This prevents recursion while maintaining proper async context isolation
_execution_stack: contextvars.ContextVar[Set[str]] = contextvars.ContextVar(
    'execution_stack', default=set()
)


def get_execution_stack() -> Set[str]:
    """
    Get current execution stack (async-safe).
    
    Returns:
        Set of absolute script paths currently being executed in this async context
    """
    return _execution_stack.get()


def push_execution(script_path: str) -> bool:
    """
    Add script to execution stack. Returns False if recursion detected.
    
    Args:
        script_path: Absolute path to script being executed
    
    Returns:
        True if script can be executed, False if recursion detected
    """
    stack = get_execution_stack()
    if script_path in stack:
        return False  # Recursion detected
    
    # Create new set (immutable pattern for contextvars)
    new_stack = stack.copy()
    new_stack.add(script_path)
    _execution_stack.set(new_stack)
    return True


def pop_execution(script_path: str):
    """
    Remove script from execution stack.
    
    Args:
        script_path: Absolute path to script that finished executing
    """
    stack = get_execution_stack()
    new_stack = stack.copy()
    new_stack.discard(script_path)
    _execution_stack.set(new_stack)

# Language execution mapping
LANGUAGE_EXEC_MAP = {
    ".py": ["python"],
    ".js": ["node"],
    ".ts": ["npx", "ts-node"],
    ".go": ["go", "run"],
    ".rs": ["cargo", "run"],
    ".java": ["java"],
    ".rb": ["ruby"],
    ".sh": ["bash"]
}

ALLOWED_EXTENSIONS = set(LANGUAGE_EXEC_MAP.keys())
MAX_RUNTIME = 300  # 5 minutes
MIN_RUNTIME = 0.1   # 100ms minimum
MAX_STDOUT_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_STDOUT_LINES = 200


async def execute_script_core(
    script_path: str,
    active_project: str,
    args: list = None,
    timeout: int = 60
) -> dict:
    """
    Core script execution logic (shared between /run-local and /execute endpoints).
    
    ✅ OPTION A: Extracted core function for internal delegation
    
    Args:
        script_path: Path to script (relative to active project or full path)
        active_project: Active project name
        args: Optional command-line arguments (list)
        timeout: Maximum execution time (1-300s, default: 60)
    
    Returns:
        dict with execution results:
        - status: "success" | "failed" | "error"
        - returncode: Process exit code
        - stdout: Standard output (truncated if large)
        - stderr: Standard error
        - script_path: Final script path used
        - runtime: Execution time in seconds
        - language: File extension (without dot)
        - timestamp: ISO timestamp
        - error_code: Error code if status is "error"
        - message: Error message if status is "error"
    """
    if args is None:
        args = []
    
    try:
        # ✅ SECURITY: Path validation
        project_dir = os.path.join("projects", active_project)
        if not os.path.exists(project_dir):
            return {
                "status": "error",
                "error_code": "PROJECT_NOT_FOUND",
                "message": f"Project directory not found: {project_dir}"
            }
        
        # ✅ Normalize script path (prevent double prefix + Windows-safe)
        script_path = script_path.replace("\\", "/").strip()
        
        # Remove leading slash if present
        if script_path.startswith("/"):
            script_path = script_path.lstrip("/")
        
        # ✅ Security check: Reject paths from other projects
        if script_path.startswith("projects/") and not script_path.startswith(f"projects/{active_project}/"):
            return {
                "status": "error",
                "error_code": "PATH_VIOLATION",
                "message": f"Script path must be relative to active project '{active_project}' or start with 'projects/{active_project}/'"
            }
        
        # ✅ Compute absolute paths first
        abs_project = os.path.abspath(os.path.join("projects", active_project))
        abs_script = os.path.abspath(script_path)
        
        if not abs_script.startswith(abs_project):
            script_path = os.path.join("projects", active_project, script_path)
            abs_script = os.path.abspath(script_path)
        
        script_path = script_path.replace("\\", "/")
        
        log_message(f"[RunLocal] Final verified absolute path: {abs_script}")
        
        if not abs_script.startswith(abs_project):
            return {
                "status": "error",
                "error_code": "PATH_VIOLATION",
                "message": "Script must be within active project"
            }
        
        # ✅ ENHANCEMENT: Async-safe recursion protection
        # Normalize absolute path for consistent tracking (Windows-safe)
        abs_script_normalized = abs_script.replace("\\", "/")
        
        # Check for recursion before execution
        if not push_execution(abs_script_normalized):
            # ✅ SECURITY: Log recursion attempt
            log_message(f"[SECURITY] ⚠️ Recursive execution blocked: {script_path}")
            log_message(f"[SECURITY] Script '{script_path}' is already being executed in this context")
            
            return {
                "status": "error",
                "error_code": "RECURSION_DETECTED",
                "message": f"Recursive execution detected: {script_path} is already being executed",
                "script_path": script_path
            }
        
        # Use try-finally to ensure cleanup even if execution fails
        try:
            file_ext = os.path.splitext(script_path)[1].lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                return {
                    "status": "error",
                    "error_code": "INVALID_EXTENSION",
                    "message": f"File extension '{file_ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                }
            
            if not os.path.exists(script_path):
                return {
                    "status": "error",
                    "error_code": "SCRIPT_NOT_FOUND",
                    "message": f"Script not found: {script_path}"
                }
            
            # Validate timeout
            if timeout < 1 or timeout > MAX_RUNTIME:
                timeout = 60
            
            # Sanitize arguments
            if not isinstance(args, list):
                args = []
            
            sanitized_args = []
            for arg in args:
                if isinstance(arg, str):
                    if any(c in arg for c in [';', '&', '|', '`', '$', '(', ')', '<', '>']):
                        log_message(f"[RunLocal] ⚠️ Unsafe arg detected, skipping: {arg[:50]}")
                        continue
                    sanitized_args.append(arg)
            
            exec_cmd = LANGUAGE_EXEC_MAP.get(file_ext)
            if not exec_cmd:
                return {
                    "status": "error",
                    "error_code": "EXECUTION_NOT_CONFIGURED",
                    "message": f"Execution command not configured for extension: {file_ext}"
                }
            
            interpreter = exec_cmd[0]
            
            if not shutil.which(interpreter):
                return {
                    "status": "error",
                    "error_code": "INTERPRETER_NOT_FOUND",
                    "message": f"{interpreter} not found. Please install {interpreter} to run {file_ext} files.",
                    "interpreter": interpreter,
                    "suggestion": f"Install {interpreter} using your system's package manager"
                }
            
            # Get relative script path for execution
            if os.path.isabs(script_path):
                script_relative = os.path.relpath(script_path, project_dir)
            elif script_path.startswith(f"projects/{active_project}/"):
                script_relative = script_path[len(f"projects/{active_project}/"):]
            else:
                script_relative = script_path
            
            cmd = exec_cmd + [script_relative] + sanitized_args
            
            log_message(f"[RunLocal] Executing within {project_dir}: {' '.join(cmd)} (timeout: {timeout}s)")
            
            # Set UTF-8 encoding for subprocess output
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            
            log_message("[RunLocal] UTF-8 mode enforced for subprocess output")
            
            # Execute script
            start_time = datetime.now()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                cwd=project_dir,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                runtime = (datetime.now() - start_time).total_seconds()
                
                log_message(f"[RunLocal] ⚠️ Script timed out after {timeout}s")
                
                return {
                    "status": "error",
                    "error_code": "RUN_TIMEOUT",
                    "message": f"Script execution timed out after {timeout}s",
                    "script_path": script_path,
                    "runtime": runtime,
                    "timeout": timeout
                }
            
            runtime = (datetime.now() - start_time).total_seconds()
            
            # Decode and truncate output
            stdout_text = stdout.decode(errors="ignore") if stdout else ""
            stderr_text = stderr.decode(errors="ignore") if stderr else ""
            
            stdout_lines = stdout_text.splitlines()
            if len(stdout_lines) > MAX_STDOUT_LINES:
                stdout_lines = stdout_lines[:MAX_STDOUT_LINES] + ["\n... (truncated)"]
                stdout_text = "\n".join(stdout_lines)
            
            if len(stdout_text.encode()) > MAX_STDOUT_SIZE:
                stdout_text = stdout_text[:MAX_STDOUT_SIZE] + "\n... (truncated)"
            
            status = "success" if process.returncode == 0 else "failed"
            
            # ✅ Integration hooks (Tasks 8.7, 8.8, 8.9, 8.10, 8.11 compatible)
            # Log execution
            from core.logs.run_logger import log_run_execution
            await asyncio.to_thread(
                log_run_execution,
                project=active_project,
                script_path=script_path,
                status=status,
                returncode=process.returncode,
                stdout=stdout_text,
                stderr=stderr_text,
                runtime=runtime,
                args=sanitized_args
            )
            
            # Update memory
            await asyncio.to_thread(
                update_memory,
                active_project,
                "run_local",
                f"Executed: {os.path.basename(script_path)}",
                extra={
                    "script_path": script_path,
                    "status": status,
                    "returncode": process.returncode,
                    "runtime": runtime
                }
            )
            
            # Trigger event
            trigger_event(
                "run_logged",
                async_mode=True,
                project=active_project,
                script_path=script_path,
                status=status,
                runtime=runtime
            )
            
            # Update snapshot (Task 8.8)
            try:
                from core.context_sync import update_snapshot
                snapshot_result = await asyncio.to_thread(
                    update_snapshot,
                    active_project,
                    {
                        "last_run": datetime.now().isoformat() + "Z",
                        "last_run_status": status,
                        "last_run_script": os.path.basename(script_path)
                    }
                )
                if snapshot_result:
                    log_message(f"[RunLocal] ✅ Snapshot updated for {active_project}")
                else:
                    log_message(f"[RunLocal] ⚠️ Snapshot update failed for {active_project}")
            except ImportError as e:
                log_message(f"[RunLocal] ⚠️ context_sync module not found: {e}")
            except Exception as e:
                log_message(f"[RunLocal] ⚠️ Failed to update snapshot: {e}")
            
            return {
                "status": status,
                "returncode": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "script_path": script_path,
                "runtime": runtime,
                "language": file_ext[1:],  # Remove dot
                "timestamp": datetime.now().isoformat()
            }
        
        finally:
            # ✅ ENHANCEMENT: Always remove script from execution stack
            pop_execution(abs_script_normalized)
        
    except Exception as e:
        # Ensure cleanup on exception (if recursion check passed but error occurred)
        if 'abs_script_normalized' in locals():
            try:
                pop_execution(abs_script_normalized)
            except:
                pass  # Ignore cleanup errors
        
        log_message(f"[RunLocal] Unexpected error in execute_script_core: {e}")
        return {
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": f"Unexpected error: {str(e)}"
        }


@router.post("/run-local", dependencies=[Depends(verify_token)])
async def run_local_script(request: Request):
    """
    Execute project scripts in multiple languages safely.
    
    ✅ TASK 8.7: Universal script execution with logging
    ✅ OPTION A: Uses shared execute_script_core() function
    
    Args:
        script_path: Path to script (relative to active project)
        args: Optional command-line arguments (list)
        timeout: Maximum execution time (1-300s, default: 60)
    
    Returns:
        Execution results with stdout/stderr
    
    Note:
        - Output is truncated to 2MB or 200 lines maximum
        - Large outputs will show "... (truncated)" indicator
        - Interpreter must be installed (python, node, go, etc.)
    """
    try:
        data = await request.json()
        script_path = data.get("script_path")
        args = data.get("args", [])
        
        if not script_path:
            return JSONResponse({
                "status": "error",
                "error_code": "MISSING_PARAMETER",
                "message": "script_path parameter is required"
            }, status_code=400)
        
        # ✅ SECURITY: Require active project
        active_project = context_manager.get_project()
        if not active_project:
            return JSONResponse({
                "status": "error",
                "error_code": "NO_ACTIVE_PROJECT",
                "message": "Active project required. Use /projects/set-active/{name}"
            }, status_code=400)
        
        # Validate timeout
        try:
            timeout = int(data.get("timeout", 60))
            if timeout < 1 or timeout > MAX_RUNTIME:
                timeout = 60
        except (ValueError, TypeError):
            timeout = 60
        
        # ✅ OPTION A: Call shared core function
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
            elif error_code == "MISSING_PARAMETER" or error_code == "INVALID_EXTENSION" or error_code == "EXECUTION_NOT_CONFIGURED":
                status_code = 400
            else:
                status_code = 500
        
        return JSONResponse(result, status_code=status_code)
        
    except json.JSONDecodeError:
        return JSONResponse({
            "status": "error",
            "error_code": "INVALID_JSON",
            "message": "Invalid JSON format"
        }, status_code=400)
        
    except Exception as e:
        log_message(f"[RunLocal] Unexpected error: {e}")
        return JSONResponse({
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": f"Unexpected error: {str(e)}"
        }, status_code=500)
