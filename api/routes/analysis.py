"""
Analysis Routes - Code analysis and testing endpoints
Extracted from agent.py for Task 7 Phase 2
"""

import os
import json
import shutil
import asyncio
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from core.auth_middleware import verify_token
from core.basic_functional import log_message
from core.event_bus import trigger_event
from utils.path_utils import is_safe_path

router = APIRouter()


# ============================================================
#  🔎 CODE ANALYSIS ENDPOINT (ASYNC + SECURE)
# ============================================================

@router.post("/analyze-code", dependencies=[Depends(verify_token)])
async def analyze_code(request: Request):
    """
    Perform AI-assisted or static code analysis on the project.
    Fully async, Cloudflare-safe, and consistent with LazyDeve standards.
    
    Args:
        target: Directory/file to analyze (default: active project core/)
        mode: "ai" (Aider) or "static" (Pylint)
        project: Project name for memory hooks (optional, uses active if not provided)
    
    Returns:
        Analysis results with status
    """
    try:
        data = await request.json()
        # 🔒 TASK 1 FIX: Use context manager instead of hardcoded default
        from core.context_manager import context_manager
        active_project = context_manager.get_project()
        default_target = f"projects/{active_project}/core/" if active_project else "projects/"
        target = data.get("target", default_target)
        mode = data.get("mode", "ai").lower()

        # 🔒 Security validation
        if not is_safe_path(target):
            log_message(f"[Analyzer] Security violation: invalid path {target}")
            return JSONResponse({
                "status": "error",
                "message": "Invalid target path (outside project directory)",
                "endpoint": "/analyze-code",
                "timestamp": datetime.now().isoformat()
            }, status_code=403)

        log_message(f"[Analyzer] Starting code analysis (mode={mode}) for {target}")

        # ------------------------------------------------------------
        # 🔧 STATIC MODE (Pylint)
        # ------------------------------------------------------------
        if mode == "static":
            if not shutil.which("pylint"):
                log_message("[Analyzer] pylint not available in environment")
                return JSONResponse({
                    "status": "error",
                    "message": "pylint not installed. Run: pip install pylint",
                    "endpoint": "/analyze-code",
                    "timestamp": datetime.now().isoformat()
                }, status_code=503)

            try:
                proc = await asyncio.create_subprocess_exec(
                    "pylint", target, "--exit-zero", "--output-format=json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=45)

                try:
                    result_data = json.loads(stdout.decode() or "[]")
                except json.JSONDecodeError:
                    result_data = {"warning": "Invalid pylint JSON output", "raw": stdout.decode()}

                log_message(f"[Analyzer] Static analysis complete for {target}")

                # Memory Hooks Integration (Task 7.7.3b)
                try:
                    from core.memory_utils import update_memory, log_project_action
                    from core.context_manager import context_manager
                    project = data.get("project") or context_manager.get_project()  # 🔒 TASK 1 FIX: No default
                    
                    # Update project memory with analysis action
                    update_memory(project, "analyze", f"Static analysis: {target[:50]}", 
                                 extra={"mode": "static", "target": target})
                    
                    # Log action to project log
                    log_project_action(project, "analyze", f"Static code analysis completed: {target[:80]}")
                    
                except Exception as memory_error:
                    # Don't fail the request if memory update fails
                    log_message(f"[Memory Hooks] Error updating memory: {memory_error}")

                return JSONResponse({
                    "status": "success",
                    "mode": "static",
                    "result": result_data,
                    "endpoint": "/analyze-code",
                    "timestamp": datetime.now().isoformat()
                }, status_code=200)

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                log_message(f"[Analyzer] Timeout during static analysis on {target}")
                return JSONResponse({
                    "status": "error",
                    "message": "Static analysis timed out (45s)",
                    "endpoint": "/analyze-code",
                    "timestamp": datetime.now().isoformat()
                }, status_code=504)

        # ------------------------------------------------------------
        # 🤖 AI MODE (Aider)
        # ------------------------------------------------------------
        elif mode == "ai":
            try:
                from core.basic_functional import run_aider_task_async
                prompt = f"Perform AI-based code review and quality analysis for {target}"
                ai_result = await run_aider_task_async(prompt, "gpt-4o-mini")

                # ✅ BUG-FIX 1: Check Aider exit code before treating as success
                if ai_result.get("returncode") != 0:
                    error_msg = ai_result.get("stderr", "Unknown error")
                    log_message(f"[Analyzer] AI analysis failed: {error_msg}")
                    
                    return JSONResponse({
                        "status": "error",
                        "mode": "ai",
                        "message": f"Aider execution failed: {error_msg[:200]}",
                        "returncode": ai_result.get("returncode"),
                        "endpoint": "/analyze-code",
                        "timestamp": datetime.now().isoformat()
                    }, status_code=500)

                log_message(f"[Analyzer] AI analysis completed for {target}")

                # Memory Hooks Integration (Task 7.7.3b)
                try:
                    from core.memory_utils import update_memory, log_project_action
                    from core.context_manager import context_manager
                    project = data.get("project") or context_manager.get_project()  # 🔒 TASK 1 FIX: No default
                    
                    # Update project memory with analysis action
                    update_memory(project, "analyze", f"AI analysis: {target[:50]}", 
                                 extra={"mode": "ai", "target": target})
                    
                    # Log action to project log
                    log_project_action(project, "analyze", f"AI code analysis completed: {target[:80]}")
                    
                except Exception as memory_error:
                    # Don't fail the request if memory update fails
                    log_message(f"[Memory Hooks] Error updating memory: {memory_error}")

                # Trigger post-action event hooks
                from core.context_manager import context_manager
                trigger_event(
                    "post_action",
                    async_mode=True,
                    project=data.get("project") or context_manager.get_project(),  # 🔒 TASK 1 FIX: No default
                    action="analyze",
                    details=f"AI analysis of {target}",
                    success=True,
                    mode="ai",
                    target=target
                )
                trigger_event("post_analyze", async_mode=True, target=target, mode="ai", result=ai_result)

                return JSONResponse({
                    "status": "success",
                    "mode": "ai",
                    "result": ai_result,
                    "endpoint": "/analyze-code",
                    "timestamp": datetime.now().isoformat()
                }, status_code=200)

            except Exception as e:
                log_message(f"[Analyzer] AI mode error: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": f"AI analysis failed: {str(e)}",
                    "endpoint": "/analyze-code",
                    "timestamp": datetime.now().isoformat()
                }, status_code=500)

        else:
            return JSONResponse({
                "status": "error",
                "message": "Invalid mode. Use 'ai' or 'static'.",
                "endpoint": "/analyze-code",
                "timestamp": datetime.now().isoformat()
            }, status_code=400)

    except json.JSONDecodeError:
        log_message("[Analyzer] Invalid JSON body received")
        return JSONResponse({
            "status": "error",
            "message": "Invalid JSON in request body",
            "endpoint": "/analyze-code",
            "timestamp": datetime.now().isoformat()
        }, status_code=400)

    except Exception as e:
        log_message(f"[Analyzer] Unexpected error: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "endpoint": "/analyze-code",
            "timestamp": datetime.now().isoformat()
        }, status_code=500)


# ============================================================
#  🧪 RUN-TESTS ENDPOINT (ASYNC + SECURE)
# ============================================================

@router.post("/run-tests", dependencies=[Depends(verify_token)])
async def run_tests(request: Request):
    """
    Run project unit/integration tests asynchronously and safely.
    
    Args:
        scope: Test directory/file to run (default: "tests/")
        filter: Test filter pattern for pytest -k option
        timeout: Maximum execution time in seconds (1-300, default: 60)
    
    Returns:
        Test execution results with stdout/stderr
    """
    try:
        data = await request.json()
        scope = data.get("scope", "tests/")
        filter_ = data.get("filter", "")

        # 🕒 Timeout validation
        try:
            timeout = int(data.get("timeout", 60))
            if timeout < 1 or timeout > 300:
                timeout = 60
        except (ValueError, TypeError):
            timeout = 60

        # 🔒 Path validation
        project_root = os.getcwd()
        abs_scope = os.path.abspath(scope)
        if not abs_scope.startswith(project_root):
            log_message(f"[Tester] Security violation: {abs_scope} outside root")
            return JSONResponse({
                "status": "error",
                "message": "Access outside project directory is forbidden",
                "endpoint": "/run-tests",
                "timestamp": datetime.now().isoformat()
            }, status_code=403)

        # 🔒 Filter sanitization
        if any(c in filter_ for c in [';', '&', '|', '`', '$', '(', ')', '<', '>', '{', '}']):
            log_message(f"[Tester] Unsafe filter: {filter_}")
            return JSONResponse({
                "status": "error",
                "message": "Unsafe filter pattern detected",
                "endpoint": "/run-tests",
                "timestamp": datetime.now().isoformat()
            }, status_code=400)

        log_message(f"[Tester] Running tests in {scope} (filter={filter_})")

        # ✅ Check pytest availability
        check_proc = await asyncio.create_subprocess_exec(
            "pytest", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(check_proc.communicate(), timeout=5)
        if check_proc.returncode != 0:
            log_message("[Tester] pytest not available")
            return JSONResponse({
                "status": "error",
                "message": "pytest not installed. Run: pip install pytest",
                "endpoint": "/run-tests",
                "timestamp": datetime.now().isoformat()
            }, status_code=503)

        # Build test command
        cmd = ["pytest", abs_scope, "-q", "--tb=short"]
        if filter_:
            cmd += ["-k", filter_]

        log_message(f"[Tester] Executing command: {' '.join(cmd)}")

        # ✅ Run tests asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            log_message(f"[Tester] Timeout after {timeout}s")
            return JSONResponse({
                "status": "error",
                "message": f"Test execution timed out after {timeout}s",
                "endpoint": "/run-tests",
                "timestamp": datetime.now().isoformat()
            }, status_code=504)

        status = "success" if process.returncode == 0 else "failed"

        log_message(f"[Tester] Tests completed (code={process.returncode})")

        # ✅ TASK 8.8: Update snapshot and log event (async-safe)
        try:
            from core.context_sync import update_snapshot
            from core.event_logger import log_event
            from core.context_manager import context_manager
            
            active_project = context_manager.get_project()
            if active_project:
                # Async-safe writes
                await asyncio.to_thread(
                    update_snapshot,
                    active_project,
                    {
                        "last_run": datetime.now().isoformat() + "Z",
                        "last_run_status": status
                    }
                )
                
                await asyncio.to_thread(
                    log_event,
                    active_project,
                    "run_logged",
                    {
                        "type": "test",
                        "status": status,
                        "scope": scope,
                        "returncode": process.returncode
                    }
                )
        except Exception as e:
            log_message(f"[RunTests] ⚠️ Context sync failed: {e}")

        return JSONResponse({
            "status": status,
            "returncode": process.returncode,
            "stdout": stdout.decode(errors="ignore"),
            "stderr": stderr.decode(errors="ignore"),
            "scope": scope,
            "filter": filter_ if filter_ else None,
            "endpoint": "/run-tests",
            "timestamp": datetime.now().isoformat()
        }, status_code=200)

    except json.JSONDecodeError:
        log_message("[Tester] Invalid JSON body")
        return JSONResponse({
            "status": "error",
            "message": "Invalid JSON format",
            "endpoint": "/run-tests",
            "timestamp": datetime.now().isoformat()
        }, status_code=400)

    except Exception as e:
        log_message(f"[Tester] Unexpected error: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "endpoint": "/run-tests",
            "timestamp": datetime.now().isoformat()
        }, status_code=500)

