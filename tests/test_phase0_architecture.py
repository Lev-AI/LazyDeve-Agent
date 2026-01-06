"""
Phase 0 Tests: Architecture Preparation
"""

import pytest
import os
from pathlib import Path


def test_directory_structure():
    """Test that all new directories exist."""
    assert os.path.exists("api"), "api/ directory should exist"
    assert os.path.exists("api/routes"), "api/routes/ directory should exist"
    assert os.path.exists("services"), "services/ directory should exist"


def test_api_init_import():
    """Test api module can be imported."""
    import api
    assert hasattr(api, "__version__")


def test_services_init_import():
    """Test services module can be imported."""
    import services
    assert hasattr(services, "__version__")


def test_dependencies_import():
    """Test api.dependencies can be imported."""
    from api.dependencies import (
        validate_project_exists,
        get_active_project,
        validate_project_name
    )
    assert callable(validate_project_exists)
    assert callable(get_active_project)
    assert callable(validate_project_name)


def test_schemas_import():
    """Test api.schemas can be imported."""
    from api.schemas import (
        MemoryResponse,
        MemoryUpdateRequest,
        ContextResponse,
        ProjectDocsResponse,
        ErrorResponse
    )
    assert MemoryResponse is not None
    assert MemoryUpdateRequest is not None
    assert ContextResponse is not None
    assert ProjectDocsResponse is not None
    assert ErrorResponse is not None


def test_tool_registry_singleton():
    """Test ToolRegistry singleton."""
    from services.tool_registry import get_tool_registry
    
    registry1 = get_tool_registry()
    registry2 = get_tool_registry()
    
    assert registry1 is registry2, "ToolRegistry should be a singleton"


def test_tool_registration():
    """Test tool registration and retrieval."""
    from services.tool_registry import get_tool_registry
    
    registry = get_tool_registry()
    
    def dummy_handler():
        pass
    
    registry.register(
        name="test_tool",
        description="Test tool",
        handler=dummy_handler,
        parameters={"param1": "string"},
        category="test"
    )
    
    tool = registry.get_tool("test_tool")
    assert tool is not None
    assert tool.name == "test_tool"
    assert tool.category == "test"
    
    # Cleanup
    registry.unregister("test_tool")


def test_tool_categories():
    """Test tool categorization."""
    from services.tool_registry import get_tool_registry
    
    registry = get_tool_registry()
    
    def handler1():
        pass
    
    def handler2():
        pass
    
    registry.register(
        name="tool1",
        description="Tool 1",
        handler=handler1,
        parameters={},
        category="memory"
    )
    
    registry.register(
        name="tool2",
        description="Tool 2",
        handler=handler2,
        parameters={},
        category="memory"
    )
    
    memory_tools = registry.get_tools_by_category("memory")
    assert len(memory_tools) >= 2
    
    # Cleanup
    registry.unregister("tool1")
    registry.unregister("tool2")


def test_tool_unregistration():
    """Test tool unregistration."""
    from services.tool_registry import get_tool_registry
    
    registry = get_tool_registry()
    
    def dummy_handler():
        pass
    
    registry.register(
        name="test_tool",
        description="Test tool",
        handler=dummy_handler,
        parameters={"param1": "string"},
        category="test"
    )
    
    assert registry.get_tool("test_tool") is not None
    
    # Unregister the tool
    registry.unregister("test_tool")
    
    assert registry.get_tool("test_tool") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
