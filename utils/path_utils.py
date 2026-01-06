"""
Path Utilities - Path extraction and validation functions
Extracted from agent.py for better modularity.
"""

import os
import re
import json
import unicodedata
from core.basic_functional import log_message


def extract_path_from_text(text: str) -> str:
    """
    Extract a file or folder path from a deletion command.
    Handles multilingual and translated commands such as:
    'удали файл test.py' or 'delete the file test.py'
    
    Enhanced version that:
    - Skips filler words ("the", "a", "an")
    - Supports Cyrillic + Latin characters
    - Properly captures filenames with extensions
    - Validates extracted paths
    """
    if not text:
        return ""
    
    # Enhanced regex that skips filler words and supports Unicode
    # Matches: delete/remove/удали/удалить + optional (the/a/an) + optional (file/folder) + filename
    match = re.search(
        r'(?:delete|remove|удали|удалить)\s+(?:the\s+|a\s+|an\s+)?'
        r'(?:file|folder|файл|папку)?\s*["\']?'
        r'([\w\-\u0400-\u04FF]+(?:\.\w+)*)["\']?',
        text,
        re.IGNORECASE,
    )
    
    if match:
        path = match.group(1).strip()
        # Sanity filter: ignore invalid or filler paths
        if path and path.lower() not in ["the", "file", "folder", "a", "an"]:
            log_message(f"[Agent] 🧩 Extracted deletion path: {path}")
            return path
    
    # Fallback: handle quoted filenames
    quoted = re.search(r'["\']([^"\']+)["\']', text)
    if quoted:
        path = quoted.group(1).strip()
        # Validate quoted path
        if path and path.lower() not in ["the", "file", "folder", "a", "an"]:
            log_message(f"[Agent] 🧩 Extracted quoted deletion path: {path}")
            return path
    
    log_message("[Agent] ⚠️ Could not extract a valid path from deletion command.")
    return ""


def extract_paths_from_text(text: str) -> list:
    """
    🌍 Universal multilingual multi-file path extractor (Two-Pass Approach).
    ✅ TASK 6.0: Enhanced with keep-list filtering, spaces handling, and folder detection.
    Supports Latin, Cyrillic, Hebrew, Arabic, CJK filenames.
    
    Two-Pass Strategy:
    PASS 1: Remove all filler words and phrases completely
    PASS 2: Extract filenames (with extensions) AND folders (without extensions)
    
    This approach prevents capturing plural markers ("s", "ы") instead of actual filenames.
    
    Handles multiple files separated by:
    - Commas: "file1.py, file2.py"
    - "and": "file1.py and file2.py"
    - Hebrew "ו": "file1.py ו file2.py"
    - Arabic "و": "file1.py و file2.py"
    - Russian "и": "file1.py и file2.py"
    
    Examples:
        'delete files test1.py, test2.py and keep data.py'
        'delete folder src'
        'delete "README - Copy.md"'
    """
    if not text:
        return []
    
    # Normalize Unicode for consistent representation
    normalized_text = unicodedata.normalize("NFKC", text.strip())
    
    # ============================================
    # ✅ TASK 6.0 BUG FIX #1: Extract "keep" lists BEFORE cleaning (preserve context)
    # ✅ TASK 6.3: Simplified to English-only patterns (translation happens before CPL)
    # ============================================
    # Detect patterns like: "keep only:", "keep:", "preserve:", "maintain:", "don't delete:"
    # ✅ TASK 6.3: English-only patterns - translation layer (translate_prompt) converts all commands
    #   to English before CPL parsing, so multilingual keep patterns are not needed.
    #   This simplifies code, improves maintainability, and ensures consistent behavior.
    # ✅ OPTIMIZATION: Stop at period+space, newline, or end to prevent greedy capture
    # ✅ OPTIMIZATION: Add stop words (but, except, however) to prevent over-capture
    # ✅ OPTIMIZATION: Use word boundaries (\b) for stop words to handle punctuation correctly
    # Example: "Keep data.py but delete test.py" → Only captures "data.py", not "data.py but delete test.py"
    # Example: "Keep data.py,but delete" → Also works (no space after comma)
    # Word boundaries prevent matching stop words inside filenames (e.g., "butter.py")
    # Note: Multilingual deletion keywords (delete, удали, מחק) are KEPT for deletion detection
    #   in the cleaning step, but keep-list patterns are English-only since translation happens first.
    keep_patterns = [
        # English patterns only (with stop words using word boundaries: but, except, however, and, or)
        r'keep\s+(?:only\s+)?(?:files?\s+)?:?\s*([^\n]+?)(?:\.\s|$|\n|\b(?:but|except|however|and|or)\b)',
        r'preserve\s+(?:files?\s+)?:?\s*([^\n]+?)(?:\.\s|$|\n|\b(?:but|except|however|and|or)\b)',
        r'maintain\s+(?:files?\s+)?:?\s*([^\n]+?)(?:\.\s|$|\n|\b(?:but|except|however|and|or)\b)',
        r"(?:don'?t|do\s+not)\s+delete\s+(?:files?\s+)?:?\s*([^\n]+?)(?:\.\s|$|\n|\b(?:but|except|however|and|or)\b)",
        r'keep\s+(?:all\s+)?(?:essential\s+)?(?:files?\s+)?:?\s*([^\n]+?)(?:\.\s|$|\n|\b(?:but|except|however|and|or)\b)',
        r'except\s+(?:files?\s+)?:?\s*([^\n]+?)(?:\.\s|$|\n|\b(?:but|however|and|or)\b)',
    ]
    
    keep_list = []
    for pattern in keep_patterns:
        matches = re.findall(pattern, normalized_text, re.IGNORECASE)
        for match in matches:
            # Extract file paths from keep clause (files with extensions)
            keep_files = re.findall(
                r'([\w\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u4E00-\u9FFF\/\s\-]+(?:[\-\w\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u4E00-\u9FFF\/\s]*)?(?:\.[\w]+)+)',
                match
            )
            keep_list.extend([f.strip() for f in keep_files if f.strip()])
    
    if keep_list:
        log_message(f"[Agent] 🛡️ Detected keep list: {keep_list}")
    
    # ============================================
    # PASS 1: Remove ALL filler words and phrases
    # ============================================
    
    cleaned = normalized_text
    
    # Remove deletion keywords (delete, remove, удали, etc.)
    cleaned = re.sub(
        r'\b(?:delete|remove|удали|удалить|מחק|حذف|删除|削除)\b',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    # Remove articles (the, a, an, את, etc.)
    cleaned = re.sub(
        r'\b(?:the|a|an|את|הקובץ|הקבצים|الملف|الملفات)\b',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    # Remove file/folder words (THIS IS KEY - removes "files" completely, preventing "s" capture)
    # Use negative lookbehind/lookahead to avoid removing "file" from hyphenated names like "test-file-1.py"
    # ✅ FIX: Don't remove "file" if it's part of a filename pattern (e.g., "my file.txt" should keep "file")
    # Strategy: First protect filenames with "file" in them, then remove standalone "file" words
    # Protect patterns like "word file.extension" (space before file, no space after) or "word-file.extension"
    protected_pattern = r'([\w\-]+\s+file\.[\w]+|[\w\-]+-file\.[\w]+)'
    protected_matches = {}
    for i, match in enumerate(re.finditer(protected_pattern, cleaned, re.IGNORECASE)):
        placeholder = f"__PROTECTED_FILE_{i}__"
        protected_matches[placeholder] = match.group(0)
        cleaned = cleaned.replace(match.group(0), placeholder, 1)
    
    # Now remove file/folder words safely
    cleaned = re.sub(
        r'(?<![\w\-])(?:file|files|folder|folders|файл|файлы|папку|папки|קובץ|קבצים|ملف|ملفات|文件|資料夾)(?![\w\-])',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    # Restore protected filenames
    for placeholder, original in protected_matches.items():
        cleaned = cleaned.replace(placeholder, original)
    
    # Remove "from the project" and similar phrases
    # ✅ TASK 6.0 BUG FIX: Enhanced to handle "from current project", "from active project", etc.
    # ✅ TASK 6.0 FIX: Pattern now handles "from current active project" (both words together)
    # Original pattern only matched "from the project" or "from project", missing "from current project"
    # This caused "3.py from current project" to not be cleaned, leading to malformed path extraction
    # The pattern (?:current\s+|active\s+)? only matched ONE of "current" or "active", not both
    # Fixed by using (?:current\s+)?(?:active\s+)? to allow both words to appear together or separately
    cleaned = re.sub(
        r'\b(?:from|из)\s+(?:the\s+)?(?:current\s+)?(?:active\s+)?(?:project|проекта)\b.*$',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    # ✅ TASK 6.0 FIX: Remove common separators (and, or) to prevent them from being captured as paths
    # This helps with commands like "Delete src, tests, and main.py"
    cleaned = re.sub(
        r'\b(?:and|or)\s+',
        ' ',
        cleaned,
        flags=re.IGNORECASE
    )
    
    log_message(f"[Agent] 🧹 Cleaned text: '{cleaned.strip()}'")
    
    # ============================================
    # ✅ TASK 6.0 BUG FIX #2 & #5: Extract filenames AND folders
    # ============================================
    # PASS 2: Extract paths (files with extensions AND folders without extensions)
    
    # STEP 1: Extract quoted paths (handles both files and folders perfectly, including spaces)
    quoted_paths = re.findall(
        r'["\']([^"\']+)["\']',
        cleaned
    )
    
    # STEP 2: Extract files with extensions
    # ✅ TASK 6.0 BUG FIX #2: Use less greedy pattern to prevent over-capture
    # Prevents matching sentence fragments like "created yesterday. file.py"
    # ✅ FIX: Improved pattern to handle spaces in unquoted filenames (e.g., "my file.txt")
    # Pattern: captures word chars/spaces/hyphens/slashes leading to extension
    # Uses lookahead to stop at comma, space, end, or separators (and/or)
    # ✅ TASK 6.0 FIX: Enhanced lookahead to reliably capture last file in lists
    # ✅ TASK 6.0 FIX: Added \s+ to lookahead to handle "1.py 2.py" (space-separated files)
    # The pattern checks for: comma, space, end of string, or "and/or" separators
    # Note: "and/or" are removed in cleaning step, but kept in pattern for edge cases
    # The `\s*$` ensures last file is captured even if there's trailing text after cleaning
    # Note: The pattern must capture the full filename including spaces before the extension
    unquoted_file_paths_raw = re.findall(
        r'([\w\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u4E00-\u9FFF\/\s\-]+?\.\w+)(?=\s*[,]|\s+(?=[\w\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u4E00-\u9FFF])|\s*$|\s+(?:and|or)(?:\s|$))',
        cleaned
    )
    
    # ✅ TASK 6.0 BUG FIX #2: Sanity check - filter out over-captured candidates (multiple periods)
    # Distinguish valid filenames (file.backup.py = 1 period) from over-captures (created yesterday. file.py = 2+ periods)
    unquoted_file_paths = []
    for candidate in unquoted_file_paths_raw:
        candidate = candidate.strip()
        # Check if filename has multiple periods (over-capture detection)
        if '.' in candidate:
            name, ext = candidate.rsplit('.', 1)
            periods_count = name.count('.')
            if periods_count <= 1:
                # Valid filename (0 or 1 period in name) - allow
                # Example: "file.backup.py" has 1 period in name, which is valid
                unquoted_file_paths.append(candidate)
            else:
                # More than one period in name = likely over-captured sentence fragment - skip
                # Example: "created yesterday. file.py" has 2 periods in name part
                log_message(f"[Agent] ⚠️ Skipping over-captured candidate (multiple periods): {candidate}")
        else:
            # No extension - might be a folder, skip for now (handled in folder extraction)
            pass
    
    # STEP 3: ✅ TASK 6.0 BUG FIX #5: Extract folders (no extension, but valid path structure)
    # Pattern: word characters, slashes, hyphens
    # Must be at least 2 chars, exclude filler words
    # ✅ FIX: Removed variable-length lookbehind (?<!\.\w+) - Python doesn't support it
    # Instead, extract candidates first, then filter out file-like strings in post-processing
    folder_candidates = re.findall(
        r'\b([\w\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u4E00-\u9FFF\/\s\-]{2,100})\b',
        cleaned
    )
    
    # Filter folders: exclude filler words and paths that look like files
    valid_folders = []
    for folder in folder_candidates:
        folder = folder.strip()
        
        # Skip if looks like a file (has extension at end)
        if re.search(r'\.\w+$', folder):
            continue
        
        # Skip filler words and separators
        if folder.lower() in ["the", "file", "folder", "files", "folders", "a", "an", "delete", "remove", "and", "or"]:
            continue
        
        # Must be at least 2 characters
        if not folder or len(folder) < 2:
            continue
        
        # ✅ TASK 6.0 FIX: Exclude malformed patterns that look like filename fragments
        # Patterns like "py  2" or "py from" are likely fragments from "1.py 2.py" or "1.py from..."
        # These should not be treated as valid folder names
        if re.search(r'^\w+\s+\d+$', folder) or re.search(r'^\w+\s+from', folder, re.IGNORECASE):
            continue
        
        # Check if it's not already captured as a file or quoted path
        if not any(folder in fp or fp in folder for fp in unquoted_file_paths + quoted_paths):
            valid_folders.append(folder)
    
    # Combine and deduplicate
    all_paths = list(set(quoted_paths + unquoted_file_paths + valid_folders))
    
    if not all_paths:
        log_message("[Agent] ⚠️ Could not extract paths from deletion command.")
        return []
    
    # ============================================
    # Validate and filter
    # ============================================
    
    valid_paths = []
    for path in all_paths:
        path = path.strip()
        
        # Must be at least 2 characters and not a filler word
        if not path or len(path) < 2 or path.lower() in ["the", "file", "folder", "files", "folders", "a", "an"]:
            continue
        
        # ✅ TASK 6.0 BUG FIX #1: Exclude files from keep list (STRICT MATCHING)
        # Normalize paths for comparison (handle spaces, case-insensitive)
        # ✅ OPTIMIZATION #3: Use only strict equality and suffix matching (no substring check)
        # Prevents false matches: "log.py" in keep list should NOT match "catalog.py"
        path_normalized = path.replace(" ", "").lower()
        is_kept = any(
            (keep_path_norm := keep_path.replace(" ", "").lower()) == path_normalized or  # Exact match
            path_normalized.endswith(keep_path_norm)  # Suffix match (for paths like "dir/log.py")
            for keep_path in keep_list
        )
        
        if is_kept:
            log_message(f"[Agent] 🛡️ Excluded from deletion (keep list): {path}")
            continue
        
        valid_paths.append(path)
        log_message(f"[Agent] 🧩 Extracted deletion path: {path}")
    
    if not valid_paths:
        log_message("[Agent] ⚠️ No valid paths extracted after filtering.")
    
    return valid_paths


def load_restricted_directories():
    """
    Load restricted directories from rules.json for protection.
    Returns list of restricted directory paths.
    """
    try:
        rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules.json")
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        
        restricted = rules.get("core_protection_rules", {}).get("restricted_directories", [])
        log_message(f"[Protection] Loaded {len(restricted)} restricted directories")
        return restricted
    except Exception as e:
        log_message(f"[Protection] Failed to load restricted directories: {e}")
        return []


def is_restricted_path(path: str) -> bool:
    """
    Check if a path is in the restricted directories list.
    Returns True if the path should be protected from deletion.
    
    Logic: Block exact matches for restricted directories, but allow their contents.
    """
    restricted_dirs = load_restricted_directories()
    if not restricted_dirs:
        return False
    
    # Normalize the path for comparison
    normalized_path = path.replace("\\", "/").rstrip("/")
    
    for restricted_dir in restricted_dirs:
        # Normalize restricted directory path
        normalized_restricted = restricted_dir.replace("\\", "/").rstrip("/")
        
        # Only block EXACT matches for restricted directories
        # This allows deletion of contents (e.g., projects/TestProject) 
        # but blocks deletion of the directory itself (e.g., projects/)
        if normalized_path == normalized_restricted:
            log_message(f"[Protection] 🚫 Blocked deletion of restricted directory: {path}")
            return True
    
    return False


def is_safe_path(path: str) -> bool:
    """
    Validate that the given path stays within allowed LazyDeve project boundaries.
    Allows access to key project directories, but prevents path traversal or external access.
    """
    base_dir = os.getcwd()
    abs_path = os.path.abspath(path)

    # Allow root-level and standard subdirectories
    allowed_prefixes = ("projects/", "core/", "tests/", "logs/")
    if path in [".", "./"] or path.startswith(allowed_prefixes):
        return True

    # Security check — disallow anything outside the working directory
    return abs_path.startswith(base_dir)

