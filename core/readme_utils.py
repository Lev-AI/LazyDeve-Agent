"""
README Utilities - Intelligent README section extraction
✅ TASK 8.9.3 ENHANCEMENT: Hybrid overview + architecture extraction
✅ IMPROVED: Universal extraction that works for any README structure
"""
import re
from typing import Optional, List


def extract_readme_summary(readme_content: str, max_chars: int = 500) -> str:
    """
    Extract intelligent README summary combining overview + architecture.
    
    Universal strategy:
    1. Extract overview from first section or "Overview" heading
    2. Detect architecture sections anywhere in README (not just overview)
    3. Fill up to max_chars aggressively from remaining content
    4. Works for any README structure (with/without headings)
    
    Args:
        readme_content: Full README content
        max_chars: Maximum characters to return (default: 500)
        
    Returns:
        Combined summary string (overview + architecture)
    """
    if not readme_content or len(readme_content) == 0:
        return ""
    
    # Step 1: Early normalization - remove markdown noise upfront
    text = readme_content.strip().replace("\r", "")
    
    # Remove code blocks (preserve text content, remove formatting)
    text = re.sub(r"```[\s\S]*?```", "", text)
    
    # Remove images
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    
    # Normalize links: [text](url) -> text (keep readable text, remove URLs)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    
    # Step 2: Section-based parsing - split by headings
    sections = re.split(r"\n(?=##+\s*)", text)
    original_sections = re.split(r"\n(?=##+\s*)", readme_content)
    
    summary_parts: List[str] = []
    overview_section = None
    architecture_section = None
    has_architecture_keywords = False
    
    # Handle content before first heading as overview/introduction
    first_section = sections[0] if sections else ""
    if first_section and not re.match(r"##+\s*", first_section):
        # This is the introduction/overview (content before first heading)
        first_section_lower = first_section.lower()
        # Check if overview contains architecture-related keywords
        has_architecture_keywords = any(keyword in first_section_lower for keyword in [
            "architecture", "structure", "design", "scheme", "system", "project structure"
        ])
        
        first_paragraphs = re.split(r"\n\s*\n", first_section.strip())
        if first_paragraphs:
            if has_architecture_keywords:
                # If architecture keywords found, extract up to 5 paragraphs
                overview_section = "\n\n".join(first_paragraphs[:min(5, len(first_paragraphs))])
            else:
                # Standard: first 1-2 paragraphs
                overview_section = "\n\n".join(first_paragraphs[:2])
    
    # Process sections with headings
    for idx, section in enumerate(sections[1:], start=1):  # Skip first section (already processed)
        heading_match = re.match(r"##+\s*([^\n]+)", section)
        if not heading_match:
            continue
            
        heading = heading_match.group(1).lower().strip()
        section_content = section[len(heading_match.group(0)):].strip()
        
        # Find overview/description sections (flexible keyword matching)
        if any(keyword in heading for keyword in [
            "description", "overview", "about", "summary", "introduction"
        ]):
            if not overview_section and section_content:
                overview_section = section_content
        
        # Find architecture/structure sections (flexible keyword matching)
        elif any(keyword in heading for keyword in [
            "architecture", "structure", "design", "system", "project structure"
        ]):
            if not architecture_section:
                # If section_content is empty after normalization (code blocks removed),
                # extract text from original content before normalization
                if not section_content or len(section_content.strip()) == 0:
                    # Get original section using index (accounting for first section offset)
                    original_idx = idx  # sections[1:] starts at index 1, so idx matches original_sections[idx]
                    if original_idx < len(original_sections):
                        original_section = original_sections[original_idx]
                        original_heading_match = re.match(r"##+\s*([^\n]+)", original_section)
                        if original_heading_match:
                            original_content = original_section[len(original_heading_match.group(0)):].strip()
                            # Extract text lines (skip code blocks and empty lines)
                            lines = original_content.split('\n')
                            text_lines = []
                            in_code_block = False
                            for line in lines[:30]:  # First 30 lines
                                if line.strip().startswith('```'):
                                    in_code_block = not in_code_block
                                    continue
                                if not in_code_block:
                                    # Remove inline code and clean
                                    cleaned_line = re.sub(r'`[^`]+`', '', line).strip()
                                    # Skip lines that are mostly symbols (ASCII art) or very short
                                    if cleaned_line and len(cleaned_line) > 10 and not re.match(r'^[│├└┌┐┘┴┬─\s]+$', cleaned_line):
                                        text_lines.append(cleaned_line)
                            if text_lines:
                                architecture_section = ' '.join(text_lines[:3])  # First 3 meaningful lines
                            else:
                                # If no text found, at least include the heading as a summary
                                clean_heading = re.sub(r'[🏗️🧠]', '', heading).strip()
                                architecture_section = f"Architecture: {clean_heading.title()}"
                else:
                    architecture_section = section_content
    
    # ✅ NEW: Detect architecture keywords anywhere in README (not just in overview)
    if not architecture_section and "architecture" in text.lower():
        arch_pattern = re.compile(
            r"(#+\s*(architecture|structure|design|scheme|system|project structure)[^\n]*\n+)([\s\S]*?)(?=\n#+\s|\Z)",
            re.IGNORECASE,
        )
        match = arch_pattern.search(text)
        if match:
            architecture_section = match.group(3).strip()
            # Limit architecture section to ~50% of max_chars to avoid dominance
            if len(architecture_section) > max_chars // 2:
                architecture_section = architecture_section[:max_chars // 2]
    
    # Step 3: Build summary from found sections
    if overview_section:
        summary_parts.append(overview_section)
    
    if architecture_section:
        summary_parts.append(architecture_section)
    
    # Step 4: Fallback - if no sections found, use first 1-2 paragraphs
    if not summary_parts:
        paragraphs = re.split(r"\n\s*\n", text)
        summary_parts = paragraphs[:2] if len(paragraphs) >= 2 else [text[:max_chars]]
    
    # Step 5: Combine and clean
    summary = "\n\n".join(summary_parts)
    
    # Clean markdown symbols (remove # from headings, normalize whitespace)
    summary = re.sub(r"#+\s*", "", summary)  # Remove heading markers
    summary = re.sub(r"\n{3,}", "\n\n", summary)  # Normalize multiple newlines
    summary = re.sub(r"[ \t]+", " ", summary)  # Normalize spaces
    summary = summary.strip()
    
    # ✅ IMPROVED: Fill remaining chars up to max_chars if available (more aggressive)
    if len(summary) < max_chars and len(text) > len(summary):
        remaining_text = text[len(summary):].strip()
        if remaining_text:
            # Add more paragraphs or content to reach closer to max_chars
            remaining_paragraphs = re.split(r"\n\s*\n", remaining_text)
            for para in remaining_paragraphs:
                para_clean = para.strip()
                if para_clean and len(summary) + len(para_clean) + 2 <= max_chars:
                    summary += "\n\n" + para_clean
                else:
                    # Try to add partial paragraph if it would help us get closer to max_chars
                    if len(summary) < max_chars * 0.8:  # If we're still far from max_chars
                        remaining_chars = max_chars - len(summary) - 2
                        if remaining_chars > 50:  # Only if meaningful space left
                            para_partial = para_clean[:remaining_chars]
                            if para_partial:
                                summary += "\n\n" + para_partial
                    break
    
    # Step 6: Truncate gracefully at word boundary if still over limit
    if len(summary) > max_chars:
        # Try to truncate at word boundary (better than line boundary)
        truncated = summary[:max_chars]
        # Find last space before limit
        last_space = truncated.rfind(" ")
        if last_space > max_chars * 0.8:  # Only if we're not losing too much
            summary = truncated[:last_space] + "…"
        else:
            # Fallback to character limit
            summary = truncated + "…"
    
    return summary
