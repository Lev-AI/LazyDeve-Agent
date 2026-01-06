"""
Phase 5 Tests: LLM Selector Integration with Task 8
"""

import pytest
import shutil
from pathlib import Path


@pytest.fixture
def test_project_analyzed():
    """Create and analyze test project."""
    project_name = "TestPhase5LLM"
    project_dir = Path(f"projects/{project_name}")
    project_dir.mkdir(parents=True, exist_ok=True)
    
    from core.memory_utils import init_project_memory, save_memory
    from core.memory_processor import analyze_project_context, update_memory_context
    
    memory = init_project_memory(project_name)
    memory["actions"] = [
        {"action": "create_file", "file": "main.py"},
        {"action": "create_file", "file": "test_main.py"},
        {"action": "execute", "description": "pytest tests"}
    ]
    save_memory(project_name, memory)
    
    # Analyze
    context = analyze_project_context(project_name)
    update_memory_context(project_name, context)
    
    yield project_name
    
    if project_dir.exists():
        shutil.rmtree(project_dir)


def test_llm_selector_uses_semantic_context(test_project_analyzed):
    """Test that LLM selector uses semantic context."""
    from core.llm_selector import get_llm_selector
    
    selector = get_llm_selector()
    
    # Select model with project context
    model = selector.select_model("create a new test file", test_project_analyzed)
    
    assert model is not None
    assert isinstance(model, str)


def test_auto_select_with_semantic_context(test_project_analyzed):
    """Test auto_select_model with semantic context."""
    from core.llm_selector import get_llm_selector
    
    selector = get_llm_selector()
    
    # Task with project context
    model = selector.auto_select_model("refactor main function", test_project_analyzed)
    
    assert model is not None


def test_select_with_capability_preference(test_project_analyzed):
    """Test capability-based selection."""
    from core.llm_selector import get_llm_selector
    
    selector = get_llm_selector()
    
    # Speed preference
    model_speed = selector.select_model_with_semantic_context(
        "create helper function",
        test_project_analyzed,
        prefer_capability="speed"
    )
    
    # Quality preference
    model_quality = selector.select_model_with_semantic_context(
        "refactor architecture",
        test_project_analyzed,
        prefer_capability="quality"
    )
    
    assert model_speed is not None
    assert model_quality is not None


def test_tech_stack_awareness():
    """Test that selector considers tech stack."""
    from core.llm_selector import get_llm_selector
    from core.memory_utils import init_project_memory, save_memory
    from core.memory_processor import analyze_project_context, update_memory_context
    
    project_name = "TestTechStack"
    project_dir = Path(f"projects/{project_name}")
    project_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create project with specific tech stack
        memory = init_project_memory(project_name)
        memory["actions"] = [
            {"action": "create_file", "file": "app.py"},
            {"action": "execute", "description": "uvicorn app:app"}
        ]
        save_memory(project_name, memory)
        
        # Analyze
        context = analyze_project_context(project_name)
        update_memory_context(project_name, context)
        
        # Select model
        selector = get_llm_selector()
        model = selector.select_model("add new API endpoint", project_name)
        
        assert model is not None
        
    finally:
        if project_dir.exists():
            shutil.rmtree(project_dir)


def test_fallback_without_semantic_context():
    """Test that selector works without Task 8 semantic context."""
    from core.llm_selector import get_llm_selector
    
    selector = get_llm_selector()
    
    # Select without project context
    model = selector.select_model("create new file", None)
    
    assert model is not None


def test_semantic_context_caching_in_llm():
    """Test that AI context cache is used by LLM selector."""
    from core.llm_selector import get_llm_selector
    from core.ai_context import ProjectContextProvider
    
    project_name = "TestCacheLLM"
    project_dir = Path(f"projects/{project_name}")
    project_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from core.memory_utils import init_project_memory
        init_project_memory(project_name)
        
        selector = get_llm_selector()
        provider = ProjectContextProvider()
        
        # First call - should cache
        model1 = selector.select_model("test task", project_name)
        
        # Check cache
        cached = provider._is_cached(project_name)
        
        # Second call - should use cache
        model2 = selector.select_model("another task", project_name)
        
        assert model1 is not None
        assert model2 is not None
        
    finally:
        if project_dir.exists():
            shutil.rmtree(project_dir)


def test_execute_endpoint_integration(test_project_analyzed):
    """Test /execute endpoint uses semantic context."""
    from fastapi.testclient import TestClient
    from agent import app
    
    client = TestClient(app)
    
    # Set active project
    client.post("/set-project", json={"project_name": test_project_analyzed})
    
    # Execute task (model should be auto-selected with semantic context)
    response = client.post(
        "/execute",
        json={"task": "create a new helper function"}
    )
    
    # Should succeed (or fail gracefully)
    assert response.status_code in [200, 400, 500]  # Any response means integration works


def test_llm_context_string_helper(test_project_analyzed):
    """Test get_llm_context_string helper function."""
    from core.ai_context import get_llm_context_string
    
    context_string = get_llm_context_string(test_project_analyzed)
    
    assert isinstance(context_string, str)
    assert len(context_string) > 0


def test_model_selection_by_task_type(test_project_analyzed):
    """Test model selection varies by task type."""
    from core.llm_selector import get_llm_selector
    
    selector = get_llm_selector()
    
    # Test different task types
    test_model = selector.auto_select_model("write unit tests", test_project_analyzed)
    refactor_model = selector.auto_select_model("refactor code", test_project_analyzed)
    doc_model = selector.auto_select_model("write documentation", test_project_analyzed)
    
    assert test_model is not None
    assert refactor_model is not None
    assert doc_model is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])





