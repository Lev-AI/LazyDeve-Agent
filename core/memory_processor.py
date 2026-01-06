"""
Memory Processor - Semantic Analysis Engine
Analyzes project context and extracts meaningful patterns
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import Counter

from core.memory_utils import load_memory, save_memory
from core.basic_functional import log_message


def analyze_project_context(project_name: str) -> Dict[str, Any]:
    """
    Main entry point: Analyze project and generate semantic context.
    
    Args:
        project_name: Name of the project
        
    Returns:
        Semantic context dictionary
    """
    try:
        log_message(f"[Analyzer] Starting semantic analysis for {project_name}")
        
        # Load memory
        memory = load_memory(project_name, auto_migrate=True)
        actions = memory.get("actions", [])
        
        if not actions:
            log_message(f"[Analyzer] No actions yet for {project_name}")
            return {
                "description": f"New project: {project_name}",
                "tech_stack": [],
                "keywords": [],
                "activity_summary": {
                    "total_actions": 0,
                    "recent_focus": None,
                    "common_operations": [],
                    "error_patterns": []
                },
                "confidence_score": 0.0,
                "last_analyzed": datetime.now().isoformat()
            }
        
        # Extract tech stack
        tech_stack = extract_tech_stack(project_name, actions)
        
        # Summarize activity
        activity_summary = summarize_activity(actions)
        
        # Generate description
        description = _generate_project_description(project_name, actions, tech_stack)
        
        # Extract keywords
        keywords = _extract_keywords(actions, description)
        
        # Read error logs
        error_patterns = []
        project_dir = Path(f"projects/{project_name}")
        log_files = list((project_dir / ".lazydeve" / "logs").glob("*.log")) if (project_dir / ".lazydeve" / "logs").exists() else []
        
        for log_file in log_files:
            errors = _read_log_file(log_file)
            error_patterns.extend(_extract_error_patterns(errors))
        
        # Calculate confidence
        confidence = _calculate_confidence_score(
            len(actions),
            len(error_patterns),
            tech_stack
        )
        
        # Build context
        semantic_context = {
            "description": description,
            "tech_stack": tech_stack,
            "keywords": keywords,
            "activity_summary": {
                "total_actions": len(actions),
                "recent_focus": activity_summary.get("recent_focus"),
                "common_operations": activity_summary.get("common_operations", []),
                "error_patterns": error_patterns[:5]  # Top 5 errors
            },
            "confidence_score": confidence,
            "last_analyzed": datetime.now().isoformat(),
            "analyzed_actions_count": len(actions)  # ✅ TASK 8.10.1.3: Track for change detection
        }
        
        log_message(f"[Analyzer] Analysis complete for {project_name} (confidence: {confidence:.2f})")
        return semantic_context
        
    except Exception as e:
        log_message(f"[Analyzer] ERROR: Error analyzing {project_name}: {str(e)}")
        return {
            "description": f"Error analyzing project: {str(e)}",
            "tech_stack": [],
            "keywords": [],
            "activity_summary": {},
            "confidence_score": 0.0,
            "last_analyzed": datetime.now().isoformat(),
            "analyzed_actions_count": 0  # ✅ TASK 8.10.1.3: Track for change detection
        }


def extract_tech_stack(project_name: str, actions: List[Dict]) -> List[str]:
    """
    Detect technologies used in project.
    
    Args:
        project_name: Name of the project
        actions: List of action dictionaries
        
    Returns:
        List of detected technologies
    """
    tech_indicators = {
        "python": [".py", "python", "pip", "pytest", "django", "flask", "fastapi"],
        "javascript": [".js", "node", "npm", "yarn", "react", "vue", "angular"],
        "typescript": [".ts", "typescript", "tsx"],
        "java": [".java", "maven", "gradle", "spring"],
        "go": [".go", "golang"],
        "rust": [".rs", "cargo"],
        "html": [".html", "html5"],
        "css": [".css", "scss", "sass"],
        "sql": [".sql", "database", "postgres", "mysql"],
        "docker": ["docker", "dockerfile", "container"],
        "git": ["git", "commit", "branch"],
        "api": ["api", "rest", "graphql", "endpoint"],
        "testing": ["test", "pytest", "jest", "mocha"],
        "fastapi": ["fastapi", "uvicorn", "pydantic"],
        "react": ["react", "jsx", "tsx"],
        "vue": ["vue", "vuex"],
        "django": ["django", "manage.py"],
        "flask": ["flask", "app.py"]
    }
    
    detected = set()
    
    # Check file extensions and action descriptions
    for action in actions:
        action_str = json.dumps(action).lower()
        
        for tech, indicators in tech_indicators.items():
            for indicator in indicators:
                if indicator in action_str:
                    detected.add(tech)
                    break
    
    # Check project directory
    try:
        project_dir = Path(f"projects/{project_name}")
        if project_dir.exists():
            # Check for common config files
            config_files = {
                "package.json": ["javascript", "node"],
                "requirements.txt": ["python"],
                "Cargo.toml": ["rust"],
                "go.mod": ["go"],
                "pom.xml": ["java", "maven"],
                "Dockerfile": ["docker"],
                "docker-compose.yml": ["docker"],
                "pytest.ini": ["python", "testing", "pytest"],
                "setup.py": ["python"]
            }
            
            for config_file, techs in config_files.items():
                if (project_dir / config_file).exists():
                    detected.update(techs)
    
    except Exception as e:
        log_message(f"[TechStack] WARNING: Error scanning {project_name}: {str(e)}")
    
    return sorted(list(detected))


def summarize_activity(actions: List[Dict]) -> Dict[str, Any]:
    """
    Extract activity patterns from actions.
    
    Args:
        actions: List of action dictionaries
        
    Returns:
        Activity summary dictionary
    """
    if not actions:
        return {
            "recent_focus": None,
            "common_operations": []
        }
    
    # Count operation types
    operations = [action.get("type", action.get("action", "unknown")) for action in actions]
    operation_counts = Counter(operations)
    common_operations = [op for op, count in operation_counts.most_common(5)]
    
    # Get recent focus (last 10 actions)
    recent_actions = actions[-10:] if len(actions) > 10 else actions
    recent_descriptions = []
    
    for action in recent_actions:
        if "description" in action:
            recent_descriptions.append(action["description"])
        elif "action" in action:
            recent_descriptions.append(action["action"])
    
    # Determine recent focus
    recent_focus = None
    if recent_descriptions:
        # Simple keyword extraction from recent actions
        keywords = []
        for desc in recent_descriptions:
            words = re.findall(r'\b\w{4,}\b', desc.lower())
            keywords.extend(words)
        
        if keywords:
            keyword_counts = Counter(keywords)
            # Exclude common words
            exclude = {"with", "from", "that", "this", "were", "been", "have", "will", "your"}
            filtered = [(k, v) for k, v in keyword_counts.most_common(3) if k not in exclude]
            if filtered:
                recent_focus = ", ".join([k for k, v in filtered])
    
    return {
        "recent_focus": recent_focus or "General development",
        "common_operations": common_operations
    }


def update_memory_context(project_name: str, context_data: Dict[str, Any]) -> bool:
    """
    Update semantic context in memory and invalidate cache.
    
    Args:
        project_name: Name of the project
        context_data: New context data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        memory = load_memory(project_name, auto_migrate=True)
        memory["semantic_context"] = context_data
        
        success = save_memory(project_name, memory)
        
        if success:
            # Invalidate AI context cache
            try:
                from core.ai_context import invalidate_project_cache
                invalidate_project_cache(project_name)
            except ImportError:
                pass  # ai_context not yet implemented
            
            log_message(f"[Memory] Updated semantic context for {project_name}")
        
        return success
        
    except Exception as e:
        log_message(f"[Memory] ERROR: Error updating context for {project_name}: {str(e)}")
        return False


def _read_log_file(log_path: Path) -> List[str]:
    """
    Parse log file and extract error messages.
    
    Args:
        log_path: Path to log file
        
    Returns:
        List of error messages
    """
    errors = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "error" in line.lower() or "exception" in line.lower() or "failed" in line.lower():
                    errors.append(line.strip())
    except Exception:
        pass
    return errors


def _extract_error_patterns(errors: List[str]) -> List[str]:
    """
    Extract common error patterns.
    
    Args:
        errors: List of error messages
        
    Returns:
        List of error pattern descriptions
    """
    if not errors:
        return []
    
    patterns = []
    error_keywords = Counter()
    
    for error in errors:
        # Extract key phrases
        if "import" in error.lower():
            error_keywords["import errors"] += 1
        elif "file" in error.lower() or "path" in error.lower():
            error_keywords["file/path errors"] += 1
        elif "permission" in error.lower():
            error_keywords["permission errors"] += 1
        elif "syntax" in error.lower():
            error_keywords["syntax errors"] += 1
        elif "connection" in error.lower() or "network" in error.lower():
            error_keywords["network errors"] += 1
        else:
            error_keywords["general errors"] += 1
    
    # Get top patterns
    for pattern, count in error_keywords.most_common(5):
        patterns.append(f"{pattern} ({count})")
    
    return patterns


def _generate_project_description(project_name: str, actions: List[Dict], tech_stack: List[str]) -> str:
    """
    Generate AI-like project description.
    
    Args:
        project_name: Name of the project
        actions: List of actions
        tech_stack: Detected technologies
        
    Returns:
        Project description string
    """
    if not actions:
        return f"New project: {project_name}"
    
    # Build description
    parts = [f"Project '{project_name}'"]
    
    if tech_stack:
        if len(tech_stack) == 1:
            parts.append(f"using {tech_stack[0]}")
        elif len(tech_stack) <= 3:
            parts.append(f"using {', '.join(tech_stack)}")
        else:
            parts.append(f"using {', '.join(tech_stack[:3])} and more")
    
    parts.append(f"with {len(actions)} development actions recorded")
    
    return " ".join(parts) + "."


def _extract_keywords(actions: List[Dict], description: str) -> List[str]:
    """
    Extract keywords from actions and description.
    
    Args:
        actions: List of actions
        description: Project description
        
    Returns:
        List of keywords
    """
    keywords = set()
    
    # Extract from description
    desc_words = re.findall(r'\b\w{4,}\b', description.lower())
    keywords.update(desc_words)
    
    # Extract from actions
    for action in actions[-20:]:  # Last 20 actions
        action_str = json.dumps(action).lower()
        words = re.findall(r'\b\w{4,}\b', action_str)
        keywords.update(words)
    
    # Filter common words
    exclude = {
        "project", "using", "with", "actions", "recorded", "development",
        "file", "create", "update", "delete", "read", "write",
        "that", "this", "from", "were", "been", "have", "will", "your"
    }
    
    filtered = [k for k in keywords if k not in exclude]
    
    return sorted(filtered)[:20]  # Top 20 keywords


def _calculate_confidence_score(actions_count: int, errors_count: int, tech_stack: List[str]) -> float:
    """
    Calculate confidence score for semantic analysis.
    
    Args:
        actions_count: Number of actions
        errors_count: Number of errors
        tech_stack: Detected technologies
        
    Returns:
        Confidence score (0.0 to 1.0)
    """
    # Base score from actions
    if actions_count == 0:
        return 0.0
    elif actions_count < 5:
        action_score = 0.3
    elif actions_count < 20:
        action_score = 0.6
    else:
        action_score = 0.9
    
    # Tech stack bonus
    tech_bonus = min(len(tech_stack) * 0.05, 0.1)
    
    # Error penalty
    error_penalty = min(errors_count * 0.02, 0.2)
    
    # Calculate final score
    confidence = max(0.0, min(1.0, action_score + tech_bonus - error_penalty))
    
    return round(confidence, 2)

