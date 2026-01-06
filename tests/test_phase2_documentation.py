"""
Phase 2 Tests: Documentation Generator
"""

import pytest
import shutil
from pathlib import Path
from datetime import datetime


@pytest.fixture
def test_project_with_memory():
    """Create test project with Task 8 memory."""
    project_name = "TestPhase2Docs"
    project_dir = Path(f"projects/{project_name}")
    lazydeve_dir = project_dir / ".lazydeve"
    lazydeve_dir.mkdir(parents=True, exist_ok=True)
    
    # Create memory with semantic context
    from core.memory_utils import init_project_memory, save_memory
    from core.memory_processor import analyze_project_context, update_memory_context
    
    memory = init_project_memory(project_name)
    
    # Add some actions
    memory["actions"] = [
        {
            "type": "create_file",
            "description": "Created main.py",
            "timestamp": datetime.now().isoformat()
        },
        {
            "type": "execute",
            "description": "Ran pytest tests",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    save_memory(project_name, memory)
    
    # Analyze to populate semantic context
    context = analyze_project_context(project_name)
    update_memory_context(project_name, context)
    
    yield project_name
    
    # Cleanup
    if project_dir.exists():
        shutil.rmtree(project_dir)


def test_generate_project_docs(test_project_with_memory):
    """Test documentation generation."""
    from core.documentation_generator import generate_project_docs
    
    docs = generate_project_docs(test_project_with_memory)
    
    assert "overview" in docs
    assert "tech_stack" in docs
    assert "activity" in docs
    assert "metadata" in docs


def test_update_readme_new(test_project_with_memory):
    """Test README creation."""
    from core.documentation_generator import update_readme
    
    result = update_readme(test_project_with_memory, force=True)
    assert result is True
    
    # Verify README exists
    readme_path = Path(f"projects/{test_project_with_memory}/README.md")
    assert readme_path.exists()
    
    # Verify content
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "AI-Generated Project Insights" in content
    assert test_project_with_memory in content


def test_update_readme_existing(test_project_with_memory):
    """Test non-destructive README update."""
    readme_path = Path(f"projects/{test_project_with_memory}/README.md")
    
    # Create initial README with user content
    user_content = f"# {test_project_with_memory}\n\nMy custom introduction.\n\n## Installation\n\nRun `pip install`\n"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(user_content)
    
    # Update with semantic section
    from core.documentation_generator import update_readme
    result = update_readme(test_project_with_memory, force=True)
    assert result is True
    
    # Verify user content preserved
    with open(readme_path, "r", encoding="utf-8") as f:
        updated_content = f.read()
    
    assert "My custom introduction" in updated_content
    assert "Installation" in updated_content
    assert "AI-Generated Project Insights" in updated_content


def test_update_readme_twice(test_project_with_memory):
    """Test that semantic section gets replaced, not duplicated."""
    from core.documentation_generator import update_readme
    
    # First update
    update_readme(test_project_with_memory, force=True)
    
    readme_path = Path(f"projects/{test_project_with_memory}/README.md")
    with open(readme_path, "r", encoding="utf-8") as f:
        first_content = f.read()
    
    # Second update
    update_readme(test_project_with_memory, force=True)
    
    with open(readme_path, "r", encoding="utf-8") as f:
        second_content = f.read()
    
    # Should have only one AI section
    count = second_content.count("AI-Generated Project Insights")
    assert count == 1


def test_should_update_readme(test_project_with_memory):
    """Test README update detection."""
    from core.documentation_generator import should_update_readme, update_readme
    
    # Should update initially
    assert should_update_readme(test_project_with_memory) is True
    
    # Update README
    update_readme(test_project_with_memory, force=True)
    
    # Should not need update now (unless force=True)
    assert should_update_readme(test_project_with_memory) is False
    assert should_update_readme(test_project_with_memory, force=True) is True


def test_delete_semantic_section(test_project_with_memory):
    """Test semantic section removal."""
    from core.documentation_generator import update_readme, delete_semantic_section
    
    # Create README with semantic section
    update_readme(test_project_with_memory, force=True)
    
    readme_path = Path(f"projects/{test_project_with_memory}/README.md")
    with open(readme_path, "r", encoding="utf-8") as f:
        content_before = f.read()
    
    assert "AI-Generated Project Insights" in content_before
    
    # Delete semantic section
    result = delete_semantic_section(test_project_with_memory)
    assert result is True
    
    # Verify removed
    with open(readme_path, "r", encoding="utf-8") as f:
        content_after = f.read()
    
    assert "AI-Generated Project Insights" not in content_after


def test_get_readme_content(test_project_with_memory):
    """Test README content retrieval."""
    from core.documentation_generator import get_readme_content, update_readme
    
    # No README yet
    content = get_readme_content(test_project_with_memory)
    assert content is None
    
    # Create README
    update_readme(test_project_with_memory, force=True)
    
    # Get content
    content = get_readme_content(test_project_with_memory)
    assert content is not None
    assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

