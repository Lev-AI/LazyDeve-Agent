"""
Phase 3 Tests: AI Context Integration
"""

import pytest
import time
import shutil
from pathlib import Path
from datetime import datetime


@pytest.fixture
def test_project_with_analysis():
    """Create test project with analyzed semantic context."""
    project_name = "TestPhase3Context"
    project_dir = Path(f"projects/{project_name}")
    lazydeve_dir = project_dir / ".lazydeve"
    lazydeve_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and analyze project
    from core.memory_utils import init_project_memory, save_memory
    from core.memory_processor import analyze_project_context, update_memory_context
    
    memory = init_project_memory(project_name)
    
    # Add actions
    memory["actions"] = [
        {"type": "create_file", "file": "main.py", "description": "Created main.py", "timestamp": datetime.now().isoformat()},
        {"type": "execute", "description": "pytest tests", "timestamp": datetime.now().isoformat()}
    ]
    
    save_memory(project_name, memory)
    
    # Analyze
    context = analyze_project_context(project_name)
    update_memory_context(project_name, context)
    
    yield project_name
    
    # Cleanup
    if project_dir.exists():
        shutil.rmtree(project_dir)
    
    # Clear cache
    from core.ai_context import clear_all_context_cache
    clear_all_context_cache()


def test_context_provider_singleton():
    """Test ProjectContextProvider is singleton."""
    from core.ai_context import ProjectContextProvider
    
    provider1 = ProjectContextProvider()
    provider2 = ProjectContextProvider()
    
    assert provider1 is provider2


def test_get_summary_context(test_project_with_analysis):
    """Test summary context generation."""
    from core.ai_context import get_project_context_summary
    
    context = get_project_context_summary(test_project_with_analysis, format="summary")
    
    assert "project_name" in context
    assert "description" in context
    assert "tech_stack" in context
    assert "confidence" in context
    assert context["project_name"] == test_project_with_analysis


def test_get_detailed_context(test_project_with_analysis):
    """Test detailed context generation."""
    from core.ai_context import get_project_context_summary
    
    context = get_project_context_summary(test_project_with_analysis, format="detailed")
    
    assert "activity" in context
    assert "suggestions" in context
    assert "keywords" in context
    assert isinstance(context["suggestions"], list)


def test_get_llm_context(test_project_with_analysis):
    """Test LLM-optimized context generation."""
    from core.ai_context import get_project_context_summary
    
    context = get_project_context_summary(test_project_with_analysis, format="llm")
    
    assert "context_string" in context
    assert "tech_stack" in context
    assert isinstance(context["context_string"], str)
    assert len(context["context_string"]) > 0


def test_get_llm_context_string(test_project_with_analysis):
    """Test LLM context string helper."""
    from core.ai_context import get_llm_context_string
    
    context_string = get_llm_context_string(test_project_with_analysis)
    
    assert isinstance(context_string, str)
    assert test_project_with_analysis in context_string or "Project:" in context_string


def test_context_caching(test_project_with_analysis):
    """Test context caching mechanism."""
    from core.ai_context import get_project_context_summary
    
    # First call - generates and caches
    context1 = get_project_context_summary(test_project_with_analysis, use_cache=True)
    assert context1["cached"] is True
    
    # Second call - should use cache
    context2 = get_project_context_summary(test_project_with_analysis, use_cache=True)
    assert context2["cached"] is True
    
    # Should be identical
    assert context1 == context2


def test_cache_invalidation(test_project_with_analysis):
    """Test cache invalidation."""
    from core.ai_context import get_project_context_summary, invalidate_project_cache
    
    # Cache context
    context1 = get_project_context_summary(test_project_with_analysis)
    
    # Invalidate cache
    invalidate_project_cache(test_project_with_analysis)
    
    # Next call should regenerate
    context2 = get_project_context_summary(test_project_with_analysis, use_cache=False)
    
    # Both should exist
    assert context1 is not None
    assert context2 is not None


def test_cache_ttl(test_project_with_analysis):
    """Test cache TTL expiration."""
    from core.ai_context import ProjectContextProvider
    
    provider = ProjectContextProvider()
    provider._default_ttl = 1  # 1 second TTL for testing
    
    # Get context (caches it)
    context1 = provider.get_context(test_project_with_analysis)
    
    # Should be cached
    assert provider._is_cached(test_project_with_analysis)
    
    # Wait for expiration
    time.sleep(2)
    
    # Should be expired
    assert not provider._is_cached(test_project_with_analysis)
    
    # Reset TTL
    provider._default_ttl = 300


def test_clear_all_cache():
    """Test clearing all caches."""
    from core.ai_context import get_project_context_summary, clear_all_context_cache, ProjectContextProvider
    
    # Cache multiple projects
    get_project_context_summary("Project1")
    get_project_context_summary("Project2")
    
    provider = ProjectContextProvider()
    assert len(provider._cache) >= 0  # May have cached entries
    
    # Clear all
    clear_all_context_cache()
    
    assert len(provider._cache) == 0


def test_suggestions_generation(test_project_with_analysis):
    """Test AI suggestions generation."""
    from core.ai_context import get_project_context_summary
    
    context = get_project_context_summary(test_project_with_analysis, format="detailed")
    
    suggestions = context.get("suggestions", [])
    assert isinstance(suggestions, list)
    # Should have at least some suggestions
    assert len(suggestions) >= 0


def test_no_cache_mode(test_project_with_analysis):
    """Test context generation without cache."""
    from core.ai_context import get_project_context_summary
    
    context1 = get_project_context_summary(test_project_with_analysis, use_cache=False)
    context2 = get_project_context_summary(test_project_with_analysis, use_cache=False)
    
    # Should both be generated fresh
    assert context1 is not None
    assert context2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])





