"""
Documentation Generator - Auto-update README with Semantic Insights
Non-destructive README updates with semantic context
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.memory_utils import load_memory, save_memory
from core.basic_functional import log_message


def should_update_readme(project_name: str, force: bool = False) -> bool:
    """
    Check if README needs updating.
    
    Args:
        project_name: Name of the project
        force: Force update regardless of last update time
        
    Returns:
        True if update needed, False otherwise
    """
    if force:
        return True
    
    try:
        memory = load_memory(project_name)
        documentation = memory.get("documentation", {})
        
        if not documentation.get("readme_last_updated"):
            return True
        
        # Check if memory was analyzed after last README update
        semantic_context = memory.get("semantic_context", {})
        last_analyzed = semantic_context.get("last_analyzed")
        last_updated = documentation.get("readme_last_updated")
        
        if last_analyzed and last_updated:
            return last_analyzed > last_updated
        
        return False
        
    except Exception as e:
        log_message(f"[DocsGen] WARNING: Error checking README for {project_name}: {str(e)}")
        return False


def generate_project_docs(project_name: str) -> Dict[str, Any]:
    """
    Generate comprehensive project documentation.
    
    Args:
        project_name: Name of the project
        
    Returns:
        Documentation dictionary with sections
    """
    try:
        memory = load_memory(project_name)
        semantic_context = memory.get("semantic_context", {})
        
        docs = {
            "overview": _generate_overview(project_name, semantic_context),
            "tech_stack": _generate_tech_stack_section(semantic_context),
            "activity": _generate_activity_section(semantic_context),
            "changelog": _generate_changelog(memory),
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "confidence": semantic_context.get("confidence_score", 0.0)
            }
        }
        
        return docs
        
    except Exception as e:
        log_message(f"[DocsGen] ERROR: Error generating docs for {project_name}: {str(e)}")
        return {}


def update_readme(
    project_name: str,
    sections: List[str] = None,
    force: bool = False
) -> bool:
    """
    Non-destructively update README with semantic insights.
    Preserves existing user content.
    
    Args:
        project_name: Name of the project
        sections: Sections to include ["overview", "tech_stack", "activity"]
        force: Force update even if recently updated
        
    Returns:
        True if updated, False otherwise
    """
    if sections is None:
        sections = ["overview", "tech_stack", "activity"]
    
    try:
        if not should_update_readme(project_name, force):
            log_message(f"[DocsGen] README for {project_name} is up-to-date")
            return False
        
        project_dir = Path(f"projects/{project_name}")
        readme_path = project_dir / "README.md"
        
        # Generate new content
        memory = load_memory(project_name)
        semantic_context = memory.get("semantic_context", {})
        
        semantic_section = _generate_semantic_section(semantic_context, sections)
        
        # Read existing README or create new
        existing_content = ""
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
        
        # Update or append semantic section
        updated_content = _merge_semantic_section(existing_content, semantic_section, project_name)
        
        # Write updated README
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        
        # Update memory
        memory["documentation"]["readme_last_updated"] = datetime.now().isoformat()
        memory["documentation"]["auto_generated"] = True
        memory["documentation"]["sections"] = sections
        save_memory(project_name, memory)
        
        log_message(f"[DocsGen] README updated for {project_name}")
        return True
        
    except Exception as e:
        log_message(f"[DocsGen] ERROR: Error updating README for {project_name}: {str(e)}")
        return False


def _generate_overview(project_name: str, semantic_context: Dict[str, Any]) -> str:
    """Generate overview section."""
    description = semantic_context.get("description", f"Project: {project_name}")
    keywords = semantic_context.get("keywords", [])
    
    overview = f"{description}\n\n"
    
    if keywords:
        overview += f"**Keywords:** {', '.join(keywords[:10])}\n"
    
    return overview


def _generate_tech_stack_section(semantic_context: Dict[str, Any]) -> str:
    """Generate tech stack section."""
    tech_stack = semantic_context.get("tech_stack", [])
    
    if not tech_stack:
        return "Tech stack detection in progress..."
    
    section = "## Tech Stack\n\n"
    
    # Group technologies
    languages = [t for t in tech_stack if t in ["python", "javascript", "typescript", "java", "go", "rust"]]
    frameworks = [t for t in tech_stack if t in ["fastapi", "django", "flask", "react", "vue", "angular"]]
    tools = [t for t in tech_stack if t not in languages + frameworks]
    
    if languages:
        section += f"**Languages:** {', '.join(languages)}\n\n"
    if frameworks:
        section += f"**Frameworks:** {', '.join(frameworks)}\n\n"
    if tools:
        section += f"**Tools:** {', '.join(tools)}\n\n"
    
    return section


def _generate_activity_section(semantic_context: Dict[str, Any]) -> str:
    """Generate activity summary section."""
    activity = semantic_context.get("activity_summary", {})
    
    section = "## Recent Activity\n\n"
    
    recent_focus = activity.get("recent_focus")
    if recent_focus:
        section += f"**Current Focus:** {recent_focus}\n\n"
    
    common_ops = activity.get("common_operations", [])
    if common_ops:
        section += f"**Common Operations:** {', '.join(common_ops[:5])}\n\n"
    
    total_actions = activity.get("total_actions", 0)
    section += f"**Total Actions:** {total_actions}\n\n"
    
    return section


def _generate_changelog(memory: Dict[str, Any]) -> str:
    """Generate changelog from recent actions."""
    actions = memory.get("actions", [])
    
    if not actions:
        return "No activity yet."
    
    # Get last 10 actions
    recent_actions = actions[-10:] if len(actions) > 10 else actions
    
    changelog = "## Recent Changes\n\n"
    
    for action in reversed(recent_actions):
        timestamp = action.get("timestamp", "Unknown")
        action_type = action.get("type", action.get("action", "Unknown"))
        description = action.get("description", "No description")
        
        # Format timestamp
        try:
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M")
            else:
                formatted_time = timestamp
        except:
            formatted_time = timestamp
        
        changelog += f"- **{formatted_time}** - {action_type}: {description}\n"
    
    changelog += "\n"
    return changelog


def _generate_semantic_section(semantic_context: Dict[str, Any], sections: List[str]) -> str:
    """
    Generate complete semantic section for README.
    
    Args:
        semantic_context: Semantic context from memory
        sections: List of sections to include
        
    Returns:
        Markdown formatted section
    """
    content = "---\n\n"
    content += "## 🤖 AI-Generated Project Insights\n\n"
    content += "*This section is auto-generated by LazyDeve Agent*\n\n"
    
    if "overview" in sections:
        description = semantic_context.get("description", "Analyzing project...")
        content += f"{description}\n\n"
    
    if "tech_stack" in sections:
        tech_stack = semantic_context.get("tech_stack", [])
        if tech_stack:
            content += "**Detected Technologies:**\n"
            for tech in tech_stack:
                content += f"- {tech}\n"
            content += "\n"
    
    if "activity" in sections:
        activity = semantic_context.get("activity_summary", {})
        recent_focus = activity.get("recent_focus")
        if recent_focus:
            content += f"**Recent Development Focus:** {recent_focus}\n\n"
        
        total_actions = activity.get("total_actions", 0)
        content += f"**Development Actions Recorded:** {total_actions}\n\n"
    
    confidence = semantic_context.get("confidence_score", 0.0)
    last_analyzed = semantic_context.get("last_analyzed", "Never")
    
    content += f"*Analysis Confidence: {confidence:.0%} | Last Updated: {last_analyzed}*\n\n"
    content += "---\n\n"
    
    return content


def _merge_semantic_section(existing_content: str, semantic_section: str, project_name: str) -> str:
    """
    Merge semantic section into existing README non-destructively.
    
    Args:
        existing_content: Current README content
        semantic_section: New semantic section
        project_name: Name of the project
        
    Returns:
        Merged content
    """
    # Check if semantic section already exists
    ai_section_pattern = r"---\s*\n\s*##\s*🤖\s*AI-Generated Project Insights.*?---\s*\n"
    
    if re.search(ai_section_pattern, existing_content, re.DOTALL):
        # Replace existing section
        updated_content = re.sub(
            ai_section_pattern,
            semantic_section,
            existing_content,
            flags=re.DOTALL
        )
        log_message(f"[DocsGen] Updated existing semantic section in {project_name} README")
        return updated_content
    else:
        # Append to end if README exists
        if existing_content.strip():
            updated_content = existing_content.rstrip() + "\n\n" + semantic_section
            log_message(f"[DocsGen] Appended semantic section to {project_name} README")
            return updated_content
        else:
            # Create new README with header
            new_content = f"# {project_name}\n\n{semantic_section}"
            log_message(f"[DocsGen] Created new README for {project_name}")
            return new_content


def get_readme_content(project_name: str) -> Optional[str]:
    """
    Get current README content.
    
    Args:
        project_name: Name of the project
        
    Returns:
        README content or None if doesn't exist
    """
    try:
        project_dir = Path(f"projects/{project_name}")
        readme_path = project_dir / "README.md"
        
        if not readme_path.exists():
            return None
        
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
            
    except Exception as e:
        log_message(f"[DocsGen] ERROR: Error reading README for {project_name}: {str(e)}")
        return None


def delete_semantic_section(project_name: str) -> bool:
    """
    Remove auto-generated semantic section from README.
    
    Args:
        project_name: Name of the project
        
    Returns:
        True if removed, False otherwise
    """
    try:
        project_dir = Path(f"projects/{project_name}")
        readme_path = project_dir / "README.md"
        
        if not readme_path.exists():
            return False
        
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove semantic section
        ai_section_pattern = r"---\s*\n\s*##\s*🤖\s*AI-Generated Project Insights.*?---\s*\n"
        updated_content = re.sub(ai_section_pattern, "", content, flags=re.DOTALL)
        
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        
        log_message(f"[DocsGen] Removed semantic section from {project_name} README")
        return True
        
    except Exception as e:
        log_message(f"[DocsGen] ERROR: Error removing semantic section: {str(e)}")
        return False





