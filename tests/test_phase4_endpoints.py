"""
Phase 4 Tests: API Endpoints
"""

import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def test_project():
    """Create test project."""
    project_name = "TestPhase4API"
    project_dir = Path(f"projects/{project_name}")
    project_dir.mkdir(parents=True, exist_ok=True)
    
    from core.memory_utils import init_project_memory, save_memory
    memory = init_project_memory(project_name)
    memory["actions"] = [
        {"action": "create_file", "file": "main.py"},
        {"action": "execute", "description": "tests"}
    ]
    save_memory(project_name, memory)
    
    yield project_name
    
    if project_dir.exists():
        shutil.rmtree(project_dir)


@pytest.fixture
def client():
    """Create test client."""
    from agent import app
    return TestClient(app)


def test_get_project_memory(client, test_project):
    """Test GET /api/v1/projects/{name}/memory"""
    response = client.get(f"/api/v1/projects/{test_project}/memory")
    
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == test_project
    assert "semantic_context" in data
    assert "actions" in data


def test_update_project_memory(client, test_project):
    """Test POST /api/v1/projects/{name}/memory/update"""
    response = client.post(
        f"/api/v1/projects/{test_project}/memory/update",
        json={"force_reanalysis": True}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "context" in data
    assert "analyzed_at" in data


def test_get_ai_context(client, test_project):
    """Test GET /api/v1/projects/{name}/memory/context"""
    response = client.get(f"/api/v1/projects/{test_project}/memory/context")
    
    assert response.status_code == 200
    data = response.json()
    assert "project_name" in data
    assert "description" in data
    assert "tech_stack" in data


def test_get_ai_context_llm_format(client, test_project):
    """Test GET /api/v1/projects/{name}/memory/context?format=llm"""
    response = client.get(
        f"/api/v1/projects/{test_project}/memory/context",
        params={"format": "llm"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "context_string" in data


def test_invalidate_context_cache(client, test_project):
    """Test POST /api/v1/projects/{name}/memory/context/invalidate"""
    response = client.post(f"/api/v1/projects/{test_project}/memory/context/invalidate")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_get_project_docs(client, test_project):
    """Test GET /api/v1/projects/{name}/docs"""
    response = client.get(f"/api/v1/projects/{test_project}/docs")
    
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == test_project
    assert "readme_exists" in data


def test_update_project_docs(client, test_project):
    """Test POST /api/v1/projects/{name}/docs/update"""
    # First analyze to populate semantic context
    client.post(
        f"/api/v1/projects/{test_project}/memory/update",
        json={"force_reanalysis": True}
    )
    
    # Update docs
    response = client.post(
        f"/api/v1/projects/{test_project}/docs/update",
        json={
            "force_update": True,
            "sections_to_include": ["overview", "tech_stack"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["readme_updated"] is True


def test_remove_semantic_section(client, test_project):
    """Test DELETE /api/v1/projects/{name}/docs/semantic-section"""
    # First create semantic section
    client.post(
        f"/api/v1/projects/{test_project}/memory/update",
        json={"force_reanalysis": True}
    )
    client.post(
        f"/api/v1/projects/{test_project}/docs/update",
        json={"force_update": True}
    )
    
    # Remove it
    response = client.delete(f"/api/v1/projects/{test_project}/docs/semantic-section")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_get_readme(client, test_project):
    """Test GET /api/v1/projects/{name}/docs/readme"""
    response = client.get(f"/api/v1/projects/{test_project}/docs/readme")
    
    assert response.status_code == 200
    data = response.json()
    assert "exists" in data
    assert "content" in data


def test_nonexistent_project(client):
    """Test endpoints with non-existent project"""
    response = client.get("/api/v1/projects/NonExistentProject/memory")
    assert response.status_code == 404


def test_route_prefix_no_conflict(client):
    """Test that /api/v1 prefix avoids conflicts with existing routes"""
    # Existing routes should still work
    response = client.get("/ping-agent")
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])





