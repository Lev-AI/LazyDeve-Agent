"""
Phase 1 Tests: Memory Migration + Processing Engine
"""

import pytest
from unittest.mock import patch, MagicMock
from core.memory_utils import init_project_memory, load_memory, backup_memory, restore_memory_from_backup, migrate_memory_to_task8
from core.memory_processor import analyze_project_context, update_memory_context

@pytest.fixture
def project_name():
    """Fixture for project name."""
    return "TestProject"

def test_init_project_memory(project_name):
    """Test memory initialization."""
    memory = init_project_memory(project_name)
    
    assert "semantic_context" in memory
    assert memory["semantic_context"]["confidence_score"] == 0.0

def test_load_memory(project_name):
    """Test loading memory."""
    init_project_memory(project_name)
    memory = load_memory(project_name, auto_migrate=False)
    
    assert memory["project_name"] == project_name
    assert "semantic_context" in memory

def test_backup_memory(project_name):
    """Test memory backup creation."""
    init_project_memory(project_name)
    result = backup_memory(project_name)
    
    assert result is True

def test_restore_memory_from_backup(project_name):
    """Test memory restoration from backup."""
    init_project_memory(project_name)
    backup_memory(project_name)
    
    # Modify memory
    memory = load_memory(project_name, auto_migrate=False)
    memory["test_field"] = "modified"
    update_memory_context(project_name, memory["semantic_context"])
    
    # Restore from backup
    result = restore_memory_from_backup(project_name)
    assert result is True
    
    # Verify restoration
    restored_memory = load_memory(project_name, auto_migrate=False)
    assert "test_field" not in restored_memory

def test_migrate_memory_to_task8(project_name):
    """Test migration to Task 8 structure."""
    init_project_memory(project_name)
    result = migrate_memory_to_task8(project_name)
    
    assert result is True
    
    # Verify structure
    memory = load_memory(project_name, auto_migrate=False)
    assert "semantic_context" in memory
    assert "documentation" in memory

def test_update_memory_context(project_name):
    """Test updating semantic context in memory."""
    init_project_memory(project_name)
    
    new_context = {
        "description": "Test project",
        "tech_stack": ["python"],
        "keywords": ["test"],
        "activity_summary": {},
        "confidence_score": 0.5,
        "last_analyzed": "2025-01-01T00:00:00Z"
    }
    
    result = update_memory_context(project_name, new_context)
    assert result is True
    
    # Verify update
    memory = load_memory(project_name, auto_migrate=False)
    assert memory["semantic_context"]["description"] == "Test project"
    assert memory["semantic_context"]["confidence_score"] == 0.5

def test_analyze_project_context(project_name):
    """Test semantic analysis."""
    init_project_memory(project_name)
    migrate_memory_to_task8(project_name)
    
    context = analyze_project_context(project_name)
    
    assert "description" in context
    assert "tech_stack" in context
    assert "keywords" in context
    assert "activity_summary" in context
    assert "confidence_score" in context
    assert "last_analyzed" in context

if __name__ == "__main__":
    pytest.main([__file__, "-v"])




