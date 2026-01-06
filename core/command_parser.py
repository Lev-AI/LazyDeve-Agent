"""
Command Precision Layer (CPL) - Python Implementation
Centralized, deterministic command routing for LazyDeve

This module consolidates HELPER 1 and HELPER 3 from execute.py into
a lightweight, regex-based command parser that provides:
- Deterministic intent detection (same input → same output)
- Centralized command routing logic
- Easy extensibility for new intents
- Foundation for MCP integration (Task 10)

Key Design Principles:
- Lightweight: Regex + keywords only (no LLM calls)
- Deterministic: Pure function, no side effects
- Non-Breaking: Falls back to Aider if intent unclear
- Loggable: All commands logged to logs/command_parser.log
- Minimal Scope: Only handles problematic routing cases (Task 8.2)

Current Intents (Minimal Scope):
- archive_project: Archive/delete a project (complex routing)
- delete_file: Delete a file (Git-driven deletion)
- update_file: Create/update a file (file operations)
- run_local: Execute a script directly (script execution) ✅ TASK 8.7.1
- execute_aider: Default fallback (send to Aider)
"""

import re
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


# Configure logging for CPL
def setup_cpl_logger():
    """Setup dedicated logger for Command Precision Layer"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / "command_parser.log"
    
    # Create logger
    cpl_logger = logging.getLogger("CPL")
    cpl_logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not cpl_logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - [CPL] - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        cpl_logger.addHandler(file_handler)
    
    return cpl_logger


# Initialize logger
cpl_logger = setup_cpl_logger()


def parse_command(task: str) -> Dict[str, Any]:
    """
    Parse a task string and determine the intent with parameters.
    
    This is the core CPL function that consolidates HELPER 1 and HELPER 3
    logic from the /execute endpoint.
    
    Args:
        task: Task description string (e.g., "archive project test_project")
        
    Returns:
        dict with:
            - intent (str): The detected intent
            - params (dict): Parameters for the intent
            - confidence (float): Confidence score (0.0-1.0)
            - original_task (str): Original task string
            - timestamp (str): ISO timestamp
            
    Intents:
        - archive_project: Archive/delete a project
        - delete_file: Delete a file
        - update_file: Create/update a file
        - run_local: Execute a script directly (✅ TASK 8.7.1)
        - execute_aider: Default fallback (send to Aider)
    """
    timestamp = datetime.now().isoformat()
    task_lower = task.lower().strip()
    
    cpl_logger.info(f"Parsing command: '{task[:100]}'")
    
    # ============================================================
    # TASK 8.1 FIX: Enhanced Archive/Delete Project Detection
    # ============================================================
    # Pre-check: Prevent false positives for analysis/update commands
    # These should go to Aider, not project management
    if any(keyword in task_lower for keyword in ["analyze", "update", "refactor", "improve"]):
        if not any(action in task_lower for action in ["delete", "remove", "archive", "create", "new"]):
            # Likely code operation, not project management - return early
            cpl_logger.info(f"Skipped analysis-type command (not project management): {task[:100]}")
            return {
                "intent": "execute_aider",
                "params": {"task": task},
                "confidence": 0.50,
                "original_task": task,
                "timestamp": timestamp,
                "extraction_source": "skipped",
                "pattern_type": "skipped"
            }
    
    # Enhanced pattern matching with support for complex phrases
    # Strategy 1: Direct regex pattern matching (most precise)
    delete_patterns = [
        r"delete\s+(?:the\s+)?project\s+(?:folder\s+)?(?:named\s+)?[\"']?([a-zA-Z0-9_-]+)[\"']?\s*(?:completely|entirely)?",
        r"remove\s+(?:the\s+)?project\s+(?:folder\s+)?(?:named\s+)?[\"']?([a-zA-Z0-9_-]+)[\"']?\s*(?:completely|entirely)?",
        r"delete\s+project\s+folder\s+(?:named\s+)?[\"']?([a-zA-Z0-9_-]+)[\"']?\s*(?:completely|entirely)?",
        r"remove\s+project\s+folder\s+(?:named\s+)?[\"']?([a-zA-Z0-9_-]+)[\"']?\s*(?:completely|entirely)?",
    ]
    
    archive_patterns = [
        r"archive\s+(?:the\s+)?project\s+(?:folder\s+)?(?:named\s+)?[\"']?([a-zA-Z0-9_-]+)[\"']?\s*(?:completely|entirely)?",
        r"move\s+(?:the\s+)?project\s+[\"']?([a-zA-Z0-9_-]+)[\"']?\s+to\s+trash",
        r"soft\s+delete\s+(?:the\s+)?project\s+[\"']?([a-zA-Z0-9_-]+)[\"']?",
    ]
    
    # Try delete patterns first (they also map to archive_project for soft delete)
    for pattern in delete_patterns:
        match = re.search(pattern, task_lower)
        if match:
            project_name = match.group(1)
            cpl_logger.debug(f"Pattern matched (delete/complex): extracted '{project_name}' via regex")
            cpl_logger.info(f"Intent: archive_project, Project: {project_name}, Confidence: 0.95")
            return {
                "intent": "archive_project",  # Soft delete
                "params": {"project_name": project_name},
                "confidence": 0.95,
                "original_task": task,
                "timestamp": timestamp,
                "extraction_source": "regex_pattern",
                "pattern_type": "complex"
            }
    
    # Try archive patterns
    for pattern in archive_patterns:
        match = re.search(pattern, task_lower)
        if match:
            project_name = match.group(1)
            cpl_logger.debug(f"Pattern matched (archive/complex): extracted '{project_name}' via regex")
            cpl_logger.info(f"Intent: archive_project, Project: {project_name}, Confidence: 0.95")
            return {
                "intent": "archive_project",
                "params": {"project_name": project_name},
                "confidence": 0.95,
                "original_task": task,
                "timestamp": timestamp,
                "extraction_source": "regex_pattern",
                "pattern_type": "complex"
            }
    
    # Strategy 2: Fallback keyword-based detection (simpler patterns)
    if "project" in task_lower:
        # Delete/remove detection
        if any(word in task_lower for word in ["delete", "remove", "удалить"]) and not any(word in task_lower for word in ["file", "function", "class", "code"]):
            words = task_lower.split()
            project_idx = words.index("project") if "project" in words else -1
            if project_idx >= 0 and project_idx + 1 < len(words):
                potential_name = words[project_idx + 1].strip(".,!?\"'")
                if re.match(r'^[a-zA-Z0-9_-]+$', potential_name):
                    cpl_logger.debug(f"Pattern matched (delete/simple): extracted '{potential_name}' via keywords")
                    cpl_logger.info(f"Intent: archive_project, Project: {potential_name}, Confidence: 0.90")
                    return {
                        "intent": "archive_project",
                        "params": {"project_name": potential_name},
                        "confidence": 0.90,
                        "original_task": task,
                        "timestamp": timestamp,
                        "extraction_source": "keyword_based",
                        "pattern_type": "simple"
                    }
        
        # Archive detection
        if any(word in task_lower for word in ["archive", "архивировать"]) and not any(word in task_lower for word in ["file", "function", "class", "code"]):
            words = task_lower.split()
            project_idx = words.index("project") if "project" in words else -1
            if project_idx >= 0 and project_idx + 1 < len(words):
                potential_name = words[project_idx + 1].strip(".,!?\"'")
                if re.match(r'^[a-zA-Z0-9_-]+$', potential_name):
                    cpl_logger.debug(f"Pattern matched (archive/simple): extracted '{potential_name}' via keywords")
                    cpl_logger.info(f"Intent: archive_project, Project: {potential_name}, Confidence: 0.90")
                    return {
                        "intent": "archive_project",
                        "params": {"project_name": potential_name},
                        "confidence": 0.90,
                        "original_task": task,
                        "timestamp": timestamp,
                        "extraction_source": "keyword_based",
                        "pattern_type": "simple"
                    }
    
    # ============================================================
    # INTENT 2: Create Project (DEPRECATED - TASK 8.2)
    # ============================================================
    # ❌ REMOVED: ChatGPT should use POST /projects/create/{name} directly
    # 
    # Rationale (Task 8.2):
    #   - Direct endpoint works perfectly via OpenAPI schema
    #   - CPL interception is unnecessary (causes confusion)
    #   - Before Task 8: HELPER 1 redirected to direct endpoint (workaround)
    #   - After Task 8.2: ChatGPT uses direct endpoint naturally
    #   - CPL should only handle problematic cases, not simple operations
    # 
    # Original code preserved for reference (commented out):
    # project_creation_phrases = [
    #     "create project", "create a project", "new project",
    #     "initialize project", "start project", "make project",
    #     "создать проект", "новый проект"  # Russian
    # ]
    # creation_detected = any(phrase in task_lower for phrase in project_creation_phrases)
    # if creation_detected:
    #     # Extract project name logic...
    #     return {"intent": "create_project", "params": {"project_name": project_name}, ...}
    # ============================================================
    
    # ============================================================
    # INTENT 3: Commit Changes (DEPRECATED - TASK 8.2)
    # ============================================================
    # ❌ REMOVED: ChatGPT should use POST /commit directly
    # 
    # Rationale (Task 8.2):
    #   - Direct endpoint works perfectly via OpenAPI schema
    #   - CPL interception is unnecessary (causes confusion)
    #   - ChatGPT should use POST /commit for Git operations
    #   - CPL should only handle problematic cases, not simple operations
    # 
    # Original code preserved for reference (commented out):
    # commit_phrases = [
    #     "commit changes", "commit the changes", "git commit",
    #     "push changes", "push to git", "сделать коммит"
    # ]
    # commit_detected = any(phrase in task_lower for phrase in commit_phrases)
    # if commit_detected:
    #     return {"intent": "commit_changes", "params": {}, ...}
    # ============================================================
    
    # ============================================================
    # INTENT 4: Delete File (deterministic file operations)
    # ✅ TASK 6.4: Unified extraction with extract_paths_from_text()
    # ============================================================
    delete_keywords = ["delete", "remove", "удали", "удалить", "מחק", "حذف", "删除", "削除"]
    
    if any(keyword in task_lower for keyword in delete_keywords):
        # ✅ TASK 6.4: Skip only project CREATION phrases, not all "project" keywords
        # This allows valid deletions like "Delete projects/X/file.py"
        project_creation_phrases = ["create project", "new project", "создать проект", "новый проект"]
        is_project_creation = any(phrase in task_lower for phrase in project_creation_phrases)
        
        if not is_project_creation:
            # ✅ TASK 6.4: Use unified extraction (same as /execute endpoint)
            from utils.path_utils import extract_paths_from_text
            
            extracted_paths = extract_paths_from_text(task)  # Use original task, not task_clean
            
            if extracted_paths:
                cpl_logger.info(f"[CPL] 🧩 Extracted {len(extracted_paths)} path(s): {extracted_paths}")
                
                # ✅ TASK 6.4: Inject project paths AFTER extraction (prevents duplication)
                if len(extracted_paths) == 1:
                    # Single file deletion
                    file_path = inject_project_path(extracted_paths[0])
                    cpl_logger.info(f"[CPL] ✅ Injection complete: {file_path}")
                    
                    result = {
                        "intent": "delete_file",
                        "params": {"file_path": file_path},  # Single string (backward compatible)
                        "confidence": 0.90,
                        "original_task": task,
                        "timestamp": timestamp,
                        "extraction_source": "unified_extractor",
                        "pattern_type": "multi_file_capable",
                        "extracted_count": 1
                    }
                else:
                    # Multi-file deletion
                    file_paths = [inject_project_path(p) for p in extracted_paths]
                    cpl_logger.info(f"[CPL] ✅ Injection complete: {len(file_paths)} path(s)")
                    
                    result = {
                        "intent": "delete_file",
                        "params": {"file_path": file_paths},  # List for multi-file
                        "confidence": 0.90,
                        "original_task": task,
                        "timestamp": timestamp,
                        "extraction_source": "unified_extractor",
                        "pattern_type": "multi_file",
                        "extracted_count": len(extracted_paths)
                    }
                
                cpl_logger.info(f"Intent: delete_file, confidence: {result['confidence']}, paths: {result['params']['file_path']}")
                return result
            else:
                # ✅ TASK 6.4: Fallback to legacy regex if extraction fails (backward compatibility)
                cpl_logger.warning(f"[CPL] ⚠️ Unified extraction failed, falling back to legacy regex")
                
                # Legacy regex fallback (for edge cases)
                task_clean = task_lower
                for keyword in delete_keywords:
                    if keyword in task_clean:
                        task_clean = task_clean.replace(keyword, "", 1)
                        break
                task_clean = task_clean.replace("file", "", 1).strip()
                
                file_pattern = r'["\']?([^"\']+\.[a-zA-Z0-9]+)["\']?'
                file_match = re.search(file_pattern, task_clean)
                
                if file_match:
                    file_path = inject_project_path(file_match.group(1).strip())
                    cpl_logger.info(f"[CPL] Fallback extraction: {file_path}")
                    
                    return {
                        "intent": "delete_file",
                        "params": {"file_path": file_path},
                        "confidence": 0.70,  # Lower confidence for fallback
                        "original_task": task,
                        "timestamp": timestamp,
                        "extraction_source": "legacy_regex_fallback",
                        "pattern_type": "simple"
                    }
    
    # ============================================================
    # INTENT 5: Read File (DEPRECATED - TASK 8.2)
    # ============================================================
    # ❌ REMOVED: ChatGPT should use POST /read-file directly
    # 
    # Rationale (Task 8.2):
    #   - Direct endpoint works perfectly via OpenAPI schema
    #   - CPL interception is unnecessary (causes confusion)
    #   - ChatGPT should use POST /read-file for file operations
    #   - CPL should only handle problematic cases, not simple operations
    # 
    # Original code preserved for reference (commented out):
    # read_keywords = ["read", "show", "display", "view", "open", "прочитай", "покажи"]
    # if any(keyword in task_lower for keyword in read_keywords):
    #     file_pattern = r'([a-zA-Z0-9_/-]+\.[a-zA-Z0-9]+)'
    #     file_match = re.search(file_pattern, task)
    #     if file_match:
    #         return {"intent": "read_file", "params": {"file_path": file_path}, ...}
    # ============================================================
    
    # ============================================================
    # INTENT 6: Update/Create File (TASK 8.3 - Stability Patch)
    # ✅ TASK 4: Enhanced with regex patterns and multilingual support
    # ============================================================
    # 🎯 PURPOSE: Handle file operations sent to /execute endpoint
    # 
    # Problem: Users send "create file test.py" to /execute
    #          → Falls back to Aider
    #          → File is NOT created (silent failure)
    # 
    # Solution: CPL detects file operations
    #          → Routes to update_file() 
    #          → File is created correctly
    # 
    # Note: This is similar to archive_project (Task 8.2)
    #       Both handle problematic routing cases through /execute
    # ============================================================
    
    # English: Regex patterns for natural language variations
    # ✅ TASK 6.4 BUG FIX: Enhanced with plural forms to handle "create three files"
    file_operation_patterns = [
        # Create variations - ENHANCED FOR PLURALS
        r"create\s+(?:a\s+)?(?:new\s+)?file",           # "create file", "create a file"
        r"create\s+(?:three|multiple|several|many)\s+(?:new\s+)?files?",  # "create three files", "create multiple files"
        r"create\s+(?:a\s+)?file\s+named",               # "create file named..."
        r"create\s+(?:a\s+)?file\s+called",              # "create file called..."
        r"create\s+(?:a\s+)?file\s+with\s+name",         # "create file with name..."
        r"create\s+files?\s+(?:named|called|with)",      # "create files named...", "create file named..."
        r"make\s+(?:a\s+)?(?:new\s+)?files?",            # "make file", "make files"
        r"add\s+(?:a\s+)?(?:new\s+)?files?",             # "add file", "add files"
        r"write\s+(?:a\s+)?(?:new\s+)?files?",            # "write file", "write files"
        r"generate\s+(?:a\s+)?(?:new\s+)?files?",         # "generate file", "generate files"
        r"new\s+files?\s+(?:named|called|with)",          # "new file named...", "new files named..."
        
        # Update/Edit variations - ENHANCED FOR PLURALS
        r"update\s+(?:the\s+)?files?",                    # "update file", "update files"
        r"edit\s+(?:the\s+)?files?",                      # "edit file", "edit files"
        r"modify\s+(?:the\s+)?files?",                    # "modify file", "modify files"
        r"change\s+(?:the\s+)?files?",                     # "change file", "change files"
        r"alter\s+(?:the\s+)?files?",                     # "alter file", "alter files"
    ]
    
    # Russian phrases (Cyrillic) - Expanded list
    russian_file_operations = [
        "создать файл",              # create file
        "создать новый файл",        # create new file
        "создай файл",                # create file (imperative)
        "создай новый файл",         # create new file (imperative)
        "создать файл с именем",      # create file named
        "создать файл под именем",    # create file under name
        "новый файл",                 # new file
        "сделать файл",               # make file
        "добавить файл",              # add file
        "написать файл",              # write file
        "обновить файл",              # update file
        "редактировать файл",         # edit file
        "изменить файл",              # change file
        "модифицировать файл",        # modify file
        "создать документ",           # create document
        "новый документ",             # new document
    ]
    
    # Hebrew phrases (Hebrew script) - New support
    hebrew_file_operations = [
        "צור קובץ",                   # create file (tzor kovetz)
        "צור קובץ חדש",              # create new file (tzor kovetz chadash)
        "צור קובץ בשם",               # create file named (tzor kovetz b'shem)
        "קובץ חדש",                   # new file (kovetz chadash)
        "הוסף קובץ",                  # add file (hosif kovetz)
        "הוסף קובץ חדש",             # add new file (hosif kovetz chadash)
        "כתוב קובץ",                  # write file (ktov kovetz)
        "עדכן קובץ",                  # update file (adken kovetz)
        "ערוך קובץ",                  # edit file (aroch kovetz)
        "שנה קובץ",                   # change file (shane kovetz)
        "צור מסמך",                   # create document (tzor masmach)
        "מסמך חדש",                   # new document (masmach chadash)
        "בנה קובץ",                   # build file (bneh kovetz)
    ]
    
    # Check if command contains file operation
    file_op_detected = False
    
    # Check regex patterns (English natural language variations)
    for pattern in file_operation_patterns:
        if re.search(pattern, task_lower):
            file_op_detected = True
            break
    
    # Check exact string matches (Russian and Hebrew)
    if not file_op_detected:
        for keyword in russian_file_operations + hebrew_file_operations:
            if keyword in task_lower:
                file_op_detected = True
                break
    
    if file_op_detected:
        # ✅ TASK 8.3 IMPROVEMENT: Better file path regex
        # Supports spaces, dots, and special characters in filenames
        # Handles quoted paths: "my file.py", 'test.backup.py'
        # Skips file operation keywords to extract only the filename
        
        # Remove file operation keywords/patterns first
        task_clean = task_lower
        for keyword in russian_file_operations + hebrew_file_operations:
            task_clean = task_clean.replace(keyword, "", 1)  # Remove first occurrence
        
        # Also remove common English patterns
        task_clean = re.sub(r"create\s+(?:a\s+)?(?:new\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"make\s+(?:a\s+)?(?:new\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"add\s+(?:a\s+)?(?:new\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"write\s+(?:a\s+)?(?:new\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"generate\s+(?:a\s+)?(?:new\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"new\s+file\s+(?:named|called|with)\s+", "", task_clean)
        task_clean = re.sub(r"update\s+(?:the\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"edit\s+(?:the\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"modify\s+(?:the\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"change\s+(?:the\s+)?file\s+", "", task_clean)
        task_clean = re.sub(r"alter\s+(?:the\s+)?file\s+", "", task_clean)
        
        # Now extract file path from cleaned string
        file_pattern = r'["\']?([^"\']+\.[a-zA-Z0-9]+)["\']?'
        file_match = re.search(file_pattern, task_clean)
        
        if file_match:
            file_path = file_match.group(1).strip()
            
            # ✅ TASK 8.3 IMPROVEMENT: Better content extraction
            # Matches until end of string (not first period)
            # Supports multi-line content and complex strings
            content_match = re.search(r'(?:with|containing|content:)\s*(.+)$', task, re.IGNORECASE | re.DOTALL)
            content = content_match.group(1).strip() if content_match else None
            
            result = {
                "intent": "update_file",
                "params": {
                    "file_path": file_path,
                    "content": content  # May be None if not specified
                },
                "confidence": 0.90 if content else 0.80,
                "original_task": task,
                "timestamp": timestamp,
                "extraction_source": "regex_pattern",
                "pattern_type": "complex"
            }
            
            cpl_logger.info(f"Intent: update_file, confidence: {result['confidence']}, file: {file_path}, has_content: {content is not None}")
            return result
    
    # ============================================================
    # INTENT 7: Run Local Script (direct execution)
    # ✅ TASK 8.7.1: CPL routing for /run-local endpoint
    # ============================================================
    # 🎯 PURPOSE: Handle script execution commands sent to /execute
    # 
    # Problem: Users send "run script.py" to /execute
    #          → Falls back to Aider
    #          → Script is NOT executed (silent failure)
    # 
    # Solution: CPL detects script execution commands
    #          → Routes to /run-local endpoint
    #          → Script is executed correctly
    # 
    # Note: Follows same pattern as update_file (Task 8.3)
    #       Only handles problematic routing cases through /execute
    # 
    # Design Principles (from Tasks 8.1-8.4):
    #   - Minimal scope: Only handle problematic cases
    #   - Pre-check patterns: Prevent false positives
    #   - Structured error responses: Don't execute directly
    #   - Confidence scores: 0.95 (regex), 0.85 (keywords), 0.50 (fallback)
    # ============================================================
    
    # ✅ TASK 8.7.1: Pre-check - Skip if this is clearly a test command
    # "run tests" or "run test suite" should go to /run-tests directly
    # ChatGPT should use POST /run-tests directly (like /projects/list)
    if "run tests" in task_lower or "run test suite" in task_lower:
        # Don't intercept - ChatGPT should use /run-tests directly
        cpl_logger.debug(f"[CPL] Skipped test command (use /run-tests directly): {task[:100]}")
    elif "test" in task_lower and ("suite" in task_lower or "all" in task_lower or "everything" in task_lower):
        # "test suite", "test all", "test everything" → /run-tests
        cpl_logger.debug(f"[CPL] Skipped test suite command (use /run-tests directly): {task[:100]}")
    else:
        # ✅ TASK 8.7.1 ENHANCEMENT: Meta-command detection
        # Handle cases where ChatGPT explicitly mentions calling /run-local endpoint
        # Examples: "Call POST /run-local to execute test_2.py"
        #           "use /run-local to run script.py"
        #           "call the /run-local endpoint with test_2.py"
        if "/run-local" in task_lower or "run-local" in task_lower:
            # Extract script path from meta-commands
            meta_patterns = [
                r"(?:execute|run|with)\s+([^\s]+\.(py|js|go|rs|java|rb|sh|ts))",  # "execute test_2.py"
                r"([^\s]+\.(py|js|go|rs|java|rb|sh|ts))",  # Fallback: any file with extension
            ]
            
            for pattern in meta_patterns:
                match = re.search(pattern, task_lower)
                if match:
                    script_path = match.group(1).strip().strip('"\'')
                    
                    # ✅ BUG-FIX 1: Allow paths starting with "projects/" (valid script paths)
                    # Improved logic: Check if it's a valid script path first, then check for project management commands
                    is_valid_script_path = (
                        script_path.startswith("projects/") or  # Valid: projects/MyProject/script.py
                        script_path.endswith(('.py', '.js', '.go', '.rs', '.java', '.rb', '.sh', '.ts'))
                    )
                    
                    # Allow valid script paths, or paths without "project" keyword
                    if is_valid_script_path:
                        # Valid script path - allow it
                        # Check if it's a test file but not a test suite command
                        if "test" in script_path.lower()[:10] and ("suite" in task_lower or "all" in task_lower):
                            continue
                        
                        cpl_logger.info(f"[CPL] ✅ Intent: run_local (meta-command), Script: {script_path}, Confidence: 0.90")
                        
                        return {
                            "intent": "run_local",
                            "params": {"script_path": script_path},
                            "confidence": 0.90,
                            "original_task": task,
                            "timestamp": timestamp,
                            "extraction_source": "meta_command",
                            "pattern_type": "endpoint_mention"
                        }
                    elif "project" in script_path.lower():
                        # Likely project management command (not a script path) - skip
                        continue
        
        # Strategy 1: Direct regex pattern matching (most precise, confidence: 0.95)
        # Patterns: "run script.py", "execute file.py", "launch script.py", "start script.py"
        # ✅ ENHANCEMENT: Added "launch" and "start" keywords for natural language support
        # ✅ BUG FIX (Task 8.8.3.1): Exclude delete commands from run_local detection
        # ✅ TASK 4.1: Exclude Git commands from run_local detection
        delete_keywords = ["delete", "remove", "удали", "удалить", "מחק", "حذف", "删除", "削除"]
        git_keywords = ["git", "commit", "push", "pull", "sync", "status", "log", "branch", 
                       "diff", "merge", "rebase", "stash", "show", "checkout", "reset", "revert", "tag"]
        if not any(keyword in task_lower for keyword in delete_keywords) and \
           not any(keyword in task_lower for keyword in git_keywords):
            # Only proceed with run_local detection if no delete keywords present
            run_local_patterns = [
                r"(?:run|execute|launch|start)\s+(?:local\s+)?([^\s]+\.(py|js|go|rs|java|rb|sh|ts))",  # "run script.py", "launch script.py", "start script.py"
                r"(?:run|execute|launch|start)\s+script\s+([^\s]+\.(py|js|go|rs|java|rb|sh|ts))",  # "run script test.py", "launch script test.py"
            ]
            
            for pattern in run_local_patterns:
                match = re.search(pattern, task_lower)
                if match:
                    script_path = match.group(1).strip()
                    
                    # ✅ TASK 8.7.1: Validate script path (basic check)
                    # Remove quotes if present
                    script_path = script_path.strip('"\'')
                    
                    # ✅ BUG-FIX 1: Allow paths starting with "projects/" (valid script paths)
                    # Improved logic: Check if it's a valid script path first
                    is_valid_script_path = (
                        script_path.startswith("projects/") or
                        script_path.endswith(('.py', '.js', '.go', '.rs', '.java', '.rb', '.sh', '.ts'))
                    )
                    
                    # Skip only if it's clearly project management (not a valid script path)
                    if not is_valid_script_path and "project" in script_path.lower():
                        continue
                    
                    cpl_logger.debug(f"[CPL] Pattern matched (run_local/complex): extracted '{script_path}' via regex")
                    cpl_logger.info(f"[CPL] ✅ Intent: run_local, Script: {script_path}, Confidence: 0.95")
                    
                    return {
                        "intent": "run_local",
                        "params": {"script_path": script_path},
                        "confidence": 0.95,
                        "original_task": task,
                        "timestamp": timestamp,
                        "extraction_source": "regex_pattern",
                        "pattern_type": "complex"
                    }
        
        # Strategy 2: Keyword-based fallback (simpler patterns, confidence: 0.85)
        # ✅ ENHANCEMENT: Added multilingual keyword support (English, Russian, Hebrew)
        # ✅ BUG FIX (Task 8.8.3.1): Exclude delete commands from run_local detection
        # ✅ TASK 4.1: Exclude Git commands from run_local detection
        # Multilingual keywords: run, execute, launch, start, выполни (ru), запусти (ru), הרץ (he)
        multilingual_keywords = [
            "run", "execute", "launch", "start",  # English
            "выполни", "запусти",  # Russian (выполни = execute, запусти = run/launch)
            "הרץ"  # Hebrew (הרץ = run)
        ]
        
        # ✅ BUG FIX (Task 8.8.3.1): Exclude delete commands - they should be handled by delete_file intent
        # ✅ TASK 4.1: Exclude Git commands - they should be handled by direct Git endpoints
        delete_keywords = ["delete", "remove", "удали", "удалить", "מחק", "حذف", "删除", "削除"]
        git_keywords = ["git", "commit", "push", "pull", "sync", "status", "log", "branch", 
                       "diff", "merge", "rebase", "stash", "show", "checkout", "reset", "revert", "tag"]
        if not any(keyword in task_lower for keyword in delete_keywords) and \
           not any(keyword in task_lower for keyword in git_keywords):
            if any(ext in task_lower for ext in [".py", ".js", ".go", ".rs", ".java", ".rb", ".sh", ".ts"]):
                # Extract file path with extension
                file_pattern = r'([^\s]+\.(py|js|go|rs|java|rb|sh|ts))'
                file_match = re.search(file_pattern, task_lower)
                
                # Check if any multilingual keyword exists in the task
                if file_match and any(keyword in task_lower for keyword in multilingual_keywords):
                    script_path = file_match.group(1).strip().strip('"\'')
                    
                    # ✅ BUG-FIX 1: Additional validation - allow valid script paths
                    # Exclude if it's clearly a test command
                    if "run tests" not in task_lower and "test suite" not in task_lower:
                        # ✅ BUG-FIX 1: Allow paths starting with "projects/" (valid script paths)
                        # Improved logic: Check if it's a valid script path first
                        is_valid_script_path = (
                            script_path.startswith("projects/") or
                            script_path.endswith(('.py', '.js', '.go', '.rs', '.java', '.rb', '.sh', '.ts'))
                        )
                        
                        # Allow valid script paths, or paths without "project" keyword
                        if is_valid_script_path:
                            # Valid script path - allow it
                            cpl_logger.debug(f"[CPL] Pattern matched (run_local/simple): extracted '{script_path}' via keywords")
                            cpl_logger.info(f"[CPL] ✅ Intent: run_local, Script: {script_path}, Confidence: 0.85")
                            
                            return {
                                "intent": "run_local",
                                "params": {"script_path": script_path},
                                "confidence": 0.85,
                                "original_task": task,
                                "timestamp": timestamp,
                                "extraction_source": "keyword_based",
                                "pattern_type": "simple"
                            }
                        # elif "project" in script_path.lower():
                        #     # Likely project management command (not a script path) - skip
                        #     # (Code will fall through to default handler)
    
    # ============================================================
    # DEFAULT: Execute via Aider (fallback)
    # ============================================================
    cpl_logger.warning(f"Fallback triggered for task: {task[:100]}")
    
    result = {
        "intent": "execute_aider",
        "params": {"task": task},
        "confidence": 0.50,
        "original_task": task,
        "timestamp": timestamp,
        "extraction_source": "fallback",
        "pattern_type": "none"
    }
    
    cpl_logger.info(f"Intent: execute_aider (fallback), confidence: {result['confidence']}")
    return result


def inject_project_path(file_path: str) -> str:
    """
    Inject active project path into file path if not already present.
    ✅ TASK 8.3: Project Context Injection
    ✅ TASK 6.1 BUG FIX #4: Detects and removes duplicate project names in paths
    
    This ensures all file operations happen within the active project directory,
    preventing accidental root directory modifications and path duplication.
    
    Args:
        file_path: Relative file path (e.g., "test.py", "src/main.py", "projects/X/X/file.py")
        
    Returns:
        str: Full path with project prefix (e.g., "projects/MyProject/test.py")
        - Removes duplicate project names if present
        - Validates cross-project paths
        - Prevents path duplication bugs
        
    Example:
        >>> # With active project "MyApp"
        >>> inject_project_path("test.py")
        'projects/MyApp/test.py'
        
        >>> # Path already has projects/ prefix
        >>> inject_project_path("projects/MyApp/test.py")
        'projects/MyApp/test.py'
        
        >>> # Path with duplicate project name (BUG FIX #4)
        >>> inject_project_path("projects/MyApp/MyApp/test.py")
        'projects/MyApp/test.py'  ← Removes duplicate
        
        >>> # Path with duplicate in different format
        >>> inject_project_path("projects/MyApp/projects/MyApp/test.py")
        'projects/MyApp/test.py'  ← Removes duplicate
        
        >>> # No active project (will be handled by protection system)
        >>> inject_project_path("test.py")
        'test.py'
    """
    from core.context_manager import context_manager
    
    # Get active project first (needed for validation)
    active_project = context_manager.get_project()
    
    # Normalize path separators for consistent processing
    normalized_file_path = file_path.replace("\\", "/")
    
    # ✅ TASK 6.1 BUG FIX: Pre-injection duplicate detection
    # Check if path contains project name as directory segment BEFORE projects/ prefix
    # Example: "test_poject_task_6/test_1.py" → Remove "test_poject_task_6/" before injection
    # This prevents: projects/test_poject_task_6/test_poject_task_6/test_1.py
    # Handles nested duplicates: "test_poject_task_6/test_poject_task_6/test_1.py" → "test_1.py"
    if active_project and not normalized_file_path.startswith("projects/"):
        # Check if path starts with project name (case-insensitive)
        project_name_pattern = re.compile(
            rf"^{re.escape(active_project)}/",
            re.IGNORECASE
        )
        # Recursively remove project name prefixes (handles nested duplicates)
        max_pre_iterations = 5  # Safety limit
        pre_iteration = 0
        while pre_iteration < max_pre_iterations:
            if project_name_pattern.match(normalized_file_path):
                # Remove project name prefix before injection
                original_path = normalized_file_path
                normalized_file_path = re.sub(
                    rf"^{re.escape(active_project)}/",
                    "",
                    normalized_file_path,
                    flags=re.IGNORECASE,
                    count=1
                )
                if pre_iteration == 0:
                    cpl_logger.info(f"[CPL] 🧹 Removed project name prefix before injection: {original_path} → {normalized_file_path}")
                else:
                    cpl_logger.info(f"[CPL] 🧹 Removed nested project name prefix: → {normalized_file_path}")
                pre_iteration += 1
            else:
                break  # No more project name prefixes found
        
        if pre_iteration >= max_pre_iterations:
            cpl_logger.warning(f"[CPL] ⚠️ Pre-injection duplicate removal reached max iterations ({max_pre_iterations})")
    
    # ✅ TASK 6.1 BUG FIX #4: Detect and remove duplicate project names/prefixes (POST-INJECTION)
    if active_project:
        # Pattern to find duplicate project name (e.g., projects/MyProject/MyProject/...)
        # ✅ FIX: Make pattern more flexible - don't require exact end match, handle any trailing content
        duplicate_project_name_pattern = re.compile(
            rf"^(projects/{re.escape(active_project)})/{re.escape(active_project)}(/.*)?$",
            re.IGNORECASE
        )
        # Pattern to find duplicate 'projects/' prefix (e.g., projects/MyProject/projects/MyProject/...)
        duplicate_projects_prefix_pattern = re.compile(
            rf"^(projects/{re.escape(active_project)})/projects/{re.escape(active_project)}(/.*)?$",
            re.IGNORECASE
        )
        
        # ✅ ADDITIONAL FIX: Handle nested duplicates (e.g., projects/X/X/X/file.py)
        # Recursively check for more duplicates until none found
        max_iterations = 5  # Safety limit to prevent infinite loops
        iteration = 0
        original_path = normalized_file_path
        
        while iteration < max_iterations:
            # Apply duplicate removal
            match_name = duplicate_project_name_pattern.match(normalized_file_path)
            match_prefix = duplicate_projects_prefix_pattern.match(normalized_file_path)
            
            if match_name:
                # Handle case where group(2) might be None (no trailing path)
                trailing = match_name.group(2) if match_name.group(2) else ""
                normalized_file_path = match_name.group(1) + trailing
                if iteration == 0:
                    cpl_logger.info(f"[CPL] 🧹 Removed duplicate project name: {original_path} → {normalized_file_path}")
                else:
                    cpl_logger.info(f"[CPL] 🧹 Removed nested duplicate project name: → {normalized_file_path}")
            elif match_prefix:
                # Handle case where group(2) might be None (no trailing path)
                trailing = match_prefix.group(2) if match_prefix.group(2) else ""
                normalized_file_path = match_prefix.group(1) + trailing
                if iteration == 0:
                    cpl_logger.info(f"[CPL] 🧹 Removed duplicate 'projects/' prefix: {original_path} → {normalized_file_path}")
                else:
                    cpl_logger.info(f"[CPL] 🧹 Removed nested duplicate 'projects/' prefix: → {normalized_file_path}")
            else:
                # No more duplicates found
                break
            
            iteration += 1
        
        if iteration >= max_iterations:
            cpl_logger.warning(f"[CPL] ⚠️ Duplicate removal reached max iterations ({max_iterations}), stopping to prevent infinite loop")
    
    # ✅ BUG FIX (Task 8.8.4): Validate cross-project paths
    # If path already has projects/ prefix, validate it belongs to active project
    if normalized_file_path.startswith("projects/"):
        if active_project:
            # Extract project name from path (use normalized path after duplicate removal)
            parts = normalized_file_path.split("/")
            if len(parts) >= 2 and parts[0] == "projects":
                path_project = parts[1]
                # Validate path belongs to active project
                if path_project != active_project:
                    cpl_logger.warning(f"[SECURITY] 🚫 Cross-project path detected: {normalized_file_path} (active: {active_project})")
                    # Correct path: extract relative path and re-inject with active project
                    relative_path = "/".join(parts[2:]) if len(parts) > 2 else parts[-1]
                    corrected_path = os.path.join("projects", active_project, relative_path)
                    cpl_logger.info(f"[SECURITY] Corrected path: {normalized_file_path} → {corrected_path}")
                    cpl_logger.info(f"[CPL][DIAG] inject_project_path input={file_path}, output={corrected_path}, active_project={active_project}, injection_applied=True, corrected=True")
                    return corrected_path
        
        # Path belongs to active project or no active project - return as-is (use normalized path)
        cpl_logger.debug(f"[CPL] Path already has projects/ prefix: {normalized_file_path}")
        cpl_logger.info(f"[CPL][DIAG] inject_project_path input={file_path}, output={normalized_file_path}, active_project={active_project}, injection_applied=False")
        return normalized_file_path
    
    if active_project:
        # Inject project path (use normalized path after duplicate removal)
        project_path = os.path.join("projects", active_project, normalized_file_path)
        cpl_logger.debug(f"[CPL] Injected project path: {normalized_file_path} → {project_path}")
        cpl_logger.info(f"[CPL][DIAG] inject_project_path input={file_path}, output={project_path}, active_project={active_project}, injection_applied=True")
        return project_path
    
    # No active project - return normalized path (will be handled by protection system)
    cpl_logger.warning(f"[CPL] No active project - file path not prefixed: {normalized_file_path}")
    cpl_logger.info(f"[CPL][DIAG] inject_project_path input={file_path}, output={normalized_file_path}, active_project=None, injection_applied=False")
    return normalized_file_path


def get_intent_action(intent: str) -> Dict[str, Any]:
    """
    Get routing information for a given intent.
    ✅ TASK 8.2: Minimized to only problematic intents
    ✅ TASK 8.7.1: Added run_local intent
    
    Returns endpoint and method for routing commands to correct handlers.
    
    Args:
        intent: Intent string (e.g., "archive_project")
        
    Returns:
        dict with:
            - endpoint: Endpoint path
            - method: HTTP method
            - handler: Handler function name
    """
    # ✅ TASK 8.2: Minimized CPL scope - only problematic intents
    # ✅ TASK 8.3: Added update_file for file operation stability
    # ✅ TASK 8.7.1: Added run_local for script execution routing
    # Removed: create_project, commit_changes, read_file (use direct endpoints)
    # Kept: archive_project, delete_file, update_file, run_local (handle problematic routing)
    intent_routing = {
        "archive_project": {
            "endpoint": "/projects/archive/{project_name}",
            "method": "POST",
            "handler": "archive_project"
        },
        "delete_file": {
            "endpoint": "/execute",  # ✅ TASK 3.6.2: RESTORED - Route to /execute (original behavior)
            "method": "POST",
            "handler": "remove_via_git"
        },
        "update_file": {  # ✅ TASK 8.3: New intent for file operations
            "endpoint": "/update-file",
            "method": "POST",
            "handler": "update_file"
        },
        "run_local": {  # ✅ TASK 8.7.1: Script execution
            "endpoint": "/run-local",
            "method": "POST",
            "handler": "run_local_script"
        },
        "execute_aider": {
            "endpoint": "/execute",
            "method": "POST",
            "handler": "run_aider_task_async"
        }
    }
    
    return intent_routing.get(intent, intent_routing["execute_aider"])


def log_parsed_command(result: Dict[str, Any]) -> None:
    """
    Log parsed command for debugging and monitoring.
    
    Args:
        result: Result from parse_command()
    """
    intent = result.get("intent", "unknown")
    confidence = result.get("confidence", 0.0)
    params = result.get("params", {})
    
    log_line = f"Intent: {intent}, Confidence: {confidence:.2f}, Params: {params}"
    cpl_logger.info(log_line)


# Export main functions
__all__ = [
    'parse_command',
    'get_intent_action',
    'log_parsed_command'
]

