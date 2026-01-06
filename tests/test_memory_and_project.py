"""
test_memory_and_project.py
--------------------------
Comprehensive unit tests for project lifecycle and memory management.

Tests cover:
- Project creation and initialization
- Memory update functionality and statistics tracking
- README auto-update triggers and thresholds
- Memory corruption recovery (invalid JSON, missing files, truncated files)
- Project action logging
- Memory statistics and analysis
- Integration tests for memory hooks in endpoints
"""

import os
import json
import tempfile
import shutil
import pytest
from unittest.mock import patch, mock_open
from datetime import datetime

# Import the modules we're testing
from core.project_manager import create_project, commit_project
from core.memory_utils import (
    init_project_memory, update_memory, load_memory, save_memory,
    log_project_action, should_update_readme, mark_readme_updated,
    get_memory_stats
)


class TestProjectCreation:
    """Test project creation and initialization."""
    
    def test_create_project_success(self, tmp_path):
        """Test successful project creation."""
        os.chdir(tmp_path)
        
        result = create_project("TestProject", "Test description", "python")
        
        assert result["status"] == "created"
        assert result["project_name"] == "TestProject"
        assert result["description"] == "Test description"
        assert result["language"] == "python"
        
        # Check project structure
        assert os.path.exists("projects/TestProject")
        assert os.path.exists("projects/TestProject/src")
        assert os.path.exists("projects/TestProject/tests")
        assert os.path.exists("projects/TestProject/docs")
        assert os.path.exists("projects/TestProject/.lazydeve")
        assert os.path.exists("projects/TestProject/.lazydeve/memory.json")
        assert os.path.exists("projects/TestProject/.lazydeve/logs")
        assert os.path.exists("projects/TestProject/README.md")
    
    def test_create_project_already_exists(self, tmp_path):
        """Test project creation when project already exists."""
        os.chdir(tmp_path)
        
        # Create project first time
        result1 = create_project("TestProject")
        assert result1["status"] == "created"
        
        # Try to create same project again
        result2 = create_project("TestProject")
        assert result2["status"] == "exists"
        assert "already exists" in result2["message"]
    
    def test_create_project_invalid_name(self, tmp_path):
        """Test project creation with invalid name."""
        os.chdir(tmp_path)
        
        # Empty name
        result = create_project("")
        assert result["status"] == "error"
        assert "cannot be empty" in result["message"]
        
        # Whitespace only
        result = create_project("   ")
        assert result["status"] == "error"
        assert "cannot be empty" in result["message"]


class TestMemoryUpdates:
    """Test memory update functionality and statistics tracking."""
    
    def test_memory_initialization(self, tmp_path):
        """Test memory initialization for new project."""
        os.chdir(tmp_path)
        
        memory = init_project_memory("TestProject", "Test description")
        
        assert memory["project_name"] == "TestProject"
        assert memory["description"] == "Test description"
        assert "stats" in memory
        assert memory["stats"]["executions"] == 0
        assert memory["stats"]["commits"] == 0
        assert memory["stats"]["analyses"] == 0
        assert memory["stats"]["total_actions"] == 0
        assert "last_updated" in memory
    
    def test_memory_update_execute(self, tmp_path):
        """Test memory update for execute action."""
        os.chdir(tmp_path)
        
        # Initialize project
        create_project("TestProject")
        
        # Update memory with execute action
        result = update_memory("TestProject", "execute", "Test execution", 
                              extra={"model": "gpt-4o", "files": ["test.py"]})
        
        assert result["status"] == "success"
        
        # Check memory was updated
        memory = load_memory("TestProject")
        assert memory["stats"]["executions"] == 1
        assert memory["stats"]["total_actions"] == 1
        assert len(memory["actions"]) == 1
        assert memory["actions"][0]["type"] == "execute"
        assert memory["actions"][0]["description"] == "Test execution"
    
    def test_memory_update_commit(self, tmp_path):
        """Test memory update for commit action."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        result = update_memory("TestProject", "commit", "Test commit", 
                              extra={"push_success": True})
        
        assert result["status"] == "success"
        
        memory = load_memory("TestProject")
        assert memory["stats"]["commits"] == 1
        assert memory["stats"]["total_actions"] == 1
    
    def test_memory_update_analyze(self, tmp_path):
        """Test memory update for analyze action."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        result = update_memory("TestProject", "analyze", "Test analysis", 
                              extra={"mode": "static", "target": "test.py"})
        
        assert result["status"] == "success"
        
        memory = load_memory("TestProject")
        assert memory["stats"]["analyses"] == 1
        assert memory["stats"]["total_actions"] == 1
    
    def test_memory_multiple_updates(self, tmp_path):
        """Test multiple memory updates."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Multiple updates
        update_memory("TestProject", "execute", "Exec 1")
        update_memory("TestProject", "commit", "Commit 1")
        update_memory("TestProject", "analyze", "Analysis 1")
        update_memory("TestProject", "execute", "Exec 2")
        
        memory = load_memory("TestProject")
        assert memory["stats"]["executions"] == 2
        assert memory["stats"]["commits"] == 1
        assert memory["stats"]["analyses"] == 1
        assert memory["stats"]["total_actions"] == 4
        assert len(memory["actions"]) == 4


class TestReadmeUpdateTriggers:
    """Test README auto-update triggers and thresholds."""
    
    def test_should_update_readme_threshold(self, tmp_path):
        """Test README update threshold logic."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Should not update with few actions
        assert should_update_readme("TestProject", threshold=5) == False
        
        # Add actions to reach threshold
        for i in range(5):
            update_memory("TestProject", "execute", f"Action {i}")
        
        # Should update after threshold
        assert should_update_readme("TestProject", threshold=5) == True
    
    def test_mark_readme_updated(self, tmp_path):
        """Test marking README as updated."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Add actions to trigger update
        for i in range(6):
            update_memory("TestProject", "execute", f"Action {i}")
        
        assert should_update_readme("TestProject") == True
        
        # Mark as updated
        result = mark_readme_updated("TestProject")
        assert result == True
        
        # Should not trigger update anymore
        assert should_update_readme("TestProject") == False


class TestMemoryCorruptionRecovery:
    """Test memory corruption recovery scenarios."""
    
    def test_load_memory_invalid_json(self, tmp_path):
        """Test loading memory with invalid JSON."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Corrupt the memory file
        memory_path = "projects/TestProject/.lazydeve/memory.json"
        with open(memory_path, "w") as f:
            f.write("invalid json content")
        
        # Should recover gracefully
        memory = load_memory("TestProject")
        assert memory["project_name"] == "TestProject"
        assert "stats" in memory
    
    def test_load_memory_missing_file(self, tmp_path):
        """Test loading memory when file is missing."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Remove memory file
        memory_path = "projects/TestProject/.lazydeve/memory.json"
        os.remove(memory_path)
        
        # Should create default memory
        memory = load_memory("TestProject")
        assert memory["project_name"] == "TestProject"
        assert "stats" in memory
    
    def test_load_memory_truncated_file(self, tmp_path):
        """Test loading memory with truncated file."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Truncate the memory file
        memory_path = "projects/TestProject/.lazydeve/memory.json"
        with open(memory_path, "w") as f:
            f.write('{"project_name": "TestProject", "stats": {')  # Incomplete JSON
        
        # Should recover gracefully
        memory = load_memory("TestProject")
        assert memory["project_name"] == "TestProject"
        assert "stats" in memory


class TestProjectActionLogging:
    """Test project action logging functionality."""
    
    def test_log_project_action(self, tmp_path):
        """Test logging project actions."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Log an action
        result = log_project_action("TestProject", "execute", "Test action executed")
        assert result == True
        
        # Check log file was created
        log_path = "projects/TestProject/.lazydeve/logs/actions.log"
        assert os.path.exists(log_path)
        
        # Check log content
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()
            assert "[EXECUTE]" in log_content
            assert "Test action executed" in log_content
    
    def test_log_multiple_actions(self, tmp_path):
        """Test logging multiple actions."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Log multiple actions
        log_project_action("TestProject", "execute", "Action 1")
        log_project_action("TestProject", "commit", "Action 2")
        log_project_action("TestProject", "analyze", "Action 3")
        
        # Check log file
        log_path = "projects/TestProject/.lazydeve/logs/actions.log"
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()
            assert "[EXECUTE]" in log_content
            assert "[COMMIT]" in log_content
            assert "[ANALYZE]" in log_content


class TestMemoryStatistics:
    """Test memory statistics and analysis."""
    
    def test_get_memory_stats(self, tmp_path):
        """Test getting memory statistics."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Add some actions
        update_memory("TestProject", "execute", "Exec 1")
        update_memory("TestProject", "execute", "Exec 2")
        update_memory("TestProject", "commit", "Commit 1")
        update_memory("TestProject", "analyze", "Analysis 1")
        
        stats = get_memory_stats("TestProject")
        
        assert stats["stats"]["executions"] == 2
        assert stats["stats"]["commits"] == 1
        assert stats["stats"]["analyses"] == 1
        assert stats["stats"]["total_actions"] == 4
        assert stats["total_actions_logged"] == 4
        assert "last_updated" in stats
    
    def test_memory_stats_empty_project(self, tmp_path):
        """Test memory stats for empty project."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        stats = get_memory_stats("TestProject")
        
        assert stats["stats"]["executions"] == 0
        assert stats["stats"]["commits"] == 0
        assert stats["stats"]["analyses"] == 0
        assert stats["stats"]["total_actions"] == 0
        assert stats["total_actions_logged"] == 0


class TestIntegrationWithEndpoints:
    """Test integration with endpoint memory hooks."""
    
    def test_memory_hooks_integration(self, tmp_path):
        """Test memory hooks integration simulation."""
        os.chdir(tmp_path)
        
        create_project("TestProject")
        
        # Simulate endpoint operations with memory hooks
        try:
            from core.memory_utils import update_memory, log_project_action
            
            # Simulate /execute endpoint
            update_memory("TestProject", "execute", "Executed: test task", 
                        extra={"model": "gpt-4o", "commit": True})
            log_project_action("TestProject", "execute", "Task executed successfully: test task")
            
            # Simulate /commit endpoint
            update_memory("TestProject", "commit", "Commit: test changes", 
                        extra={"push_success": True})
            log_project_action("TestProject", "commit", "Changes committed: test changes")
            
            # Simulate /analyze-code endpoint
            update_memory("TestProject", "analyze", "Static analysis: test.py", 
                        extra={"mode": "static", "target": "test.py"})
            log_project_action("TestProject", "analyze", "Static code analysis completed: test.py")
            
            # Verify all actions were recorded
            memory = load_memory("TestProject")
            assert memory["stats"]["executions"] == 1
            assert memory["stats"]["commits"] == 1
            assert memory["stats"]["analyses"] == 1
            assert memory["stats"]["total_actions"] == 3
            
        except Exception as memory_error:
            pytest.fail(f"Memory hooks integration failed: {memory_error}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
