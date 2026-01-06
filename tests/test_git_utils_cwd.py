"""
Test suite for Git utilities cwd parameter (Task 3.1 verification)
Tests that all Git functions accept and properly use the cwd parameter.
"""
import os
import pytest
from utils.git_utils import (
    safe_git_add,
    safe_git_commit,
    safe_git_push,
    safe_git_pull,
    safe_git_status,
    safe_git_rm,
    remove_via_git,
    remove_via_git_multi
)


def test_safe_git_status_without_cwd():
    """Test backward compatibility: safe_git_status works without cwd parameter."""
    result = safe_git_status()
    assert result["status"] in ["success", "error"]
    assert "cwd" in result
    assert result["cwd"] is None  # No cwd provided


def test_safe_git_status_with_cwd():
    """Test that safe_git_status accepts and uses cwd parameter."""
    result = safe_git_status(cwd=".")
    assert result["status"] == "success"
    assert result["cwd"] == "."


def test_invalid_cwd_returns_error():
    """Test that invalid cwd path returns proper error."""
    result = safe_git_commit("test", cwd="invalid_path_xyz/")
    assert result["status"] == "error"
    assert result["cwd"] == "invalid_path_xyz/"
    assert "error" in result


def test_all_git_functions_accept_cwd():
    """Test that all Git wrapper functions have cwd parameter."""
    import inspect
    
    functions = [
        safe_git_add,
        safe_git_commit,
        safe_git_push,
        safe_git_pull,
        safe_git_status,
        safe_git_rm,
        remove_via_git,
        remove_via_git_multi
    ]
    
    for func in functions:
        sig = inspect.signature(func)
        assert "cwd" in sig.parameters, f"{func.__name__} missing cwd parameter"
        # cwd should have a default value of None
        assert sig.parameters["cwd"].default is None, f"{func.__name__} cwd default should be None"


def test_cwd_parameter_propagates_to_result():
    """Test that cwd parameter appears in the result dict for debugging."""
    cwd_value = "."
    result = safe_git_status(cwd=cwd_value)
    assert "cwd" in result
    assert result["cwd"] == cwd_value


@pytest.mark.skipif(
    not os.path.exists("projects/Project_test_2/.git"),
    reason="Project_test_2 not yet migrated (Task 3.3 pending)"
)
def test_git_operations_in_project_directory():
    """
    Test Git operations work in project directory.
    This test will run after Task 3.3 (Migrate Existing Projects) is complete.
    """
    project_path = "projects/Project_test_2"
    
    # Test status in project
    result = safe_git_status(cwd=project_path)
    assert result["status"] == "success"
    assert result["cwd"] == project_path
    
    # Create test file
    test_file = os.path.join(project_path, "test_cwd_verification.txt")
    with open(test_file, "w") as f:
        f.write("Task 3.1 verification test\n")
    
    # Test add
    add_result = safe_git_add(cwd=project_path)
    assert add_result["status"] == "success"
    
    # Test commit
    commit_result = safe_git_commit(
        "test: Task 3.1 cwd verification",
        cwd=project_path
    )
    assert commit_result["status"] == "success"
    assert commit_result["cwd"] == project_path
    
    # Clean up
    os.remove(test_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


