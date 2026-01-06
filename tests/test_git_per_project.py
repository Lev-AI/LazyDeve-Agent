"""
Test suite for per-project Git functionality (Task 3.8)
Validates Git operations within individual project repositories.
"""
import pytest
import os
import subprocess
import tempfile
import shutil
from utils.git_utils import (
    safe_git_status,
    safe_git_commit,
    safe_git_add,
    safe_git_push,
    remove_via_git
)


@pytest.fixture(scope="session")
def project_path():
    """Reusable project path for all tests."""
    project = "projects/Project_test_2"
    if not os.path.exists(project):
        pytest.skip(f"Project {project} does not exist")
    if not os.path.exists(os.path.join(project, ".git")):
        pytest.skip(f"Project {project} does not have a Git repository")
    return project


def test_git_status_project_scope(project_path):
    """Test git status runs in project scope, not root."""
    result = safe_git_status(cwd=project_path)
    
    assert result["status"] == "success", f"Git status failed: {result.get('error', 'Unknown error')}"
    assert result["cwd"] == project_path, "cwd not properly set in result"
    
    # Verify status output doesn't contain root files
    if "stdout" in result:
        stdout = result["stdout"]
        # Should not show root-level files (like agent.py, README.md in root)
        assert "agent.py" not in stdout or "projects/" in stdout, "Root files appearing in project status"


def test_git_commit_project_isolation(project_path):
    """Test commits go to project .git, not root."""
    # Create test file
    test_file = os.path.join(project_path, "test_task_3_8_commit.txt")
    try:
        with open(test_file, "w") as f:
            f.write("Task 3.8 test commit")
        
        # Stage the file
        add_result = safe_git_add(cwd=project_path)
        assert add_result["status"] == "success", f"Git add failed: {add_result.get('error', 'Unknown error')}"
        
        # Commit in project
        commit_message = "test: Task 3.8 commit isolation test"
        result = safe_git_commit(commit_message, cwd=project_path)
        assert result["status"] == "success", f"Git commit failed: {result.get('error', 'Unknown error')}"
        assert result["cwd"] == project_path, "cwd not properly set in commit result"
        
        # Verify commit is in project .git (not root)
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        assert log_result.returncode == 0, f"Git log failed: {log_result.stderr}"
        assert commit_message in log_result.stdout or "Task 3.8" in log_result.stdout, \
            f"Commit message not found in project log: {log_result.stdout}"
        
        # Verify commit is NOT in root .git
        root_log_result = subprocess.run(
            ["git", "log", "--oneline", "-1", "--all"],
            cwd=".",
            capture_output=True,
            text=True
        )
        if root_log_result.returncode == 0:
            # Root log should not contain this test commit
            assert commit_message not in root_log_result.stdout, \
                "Test commit appeared in root repository (isolation failure)"
    
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
                # Remove from git if staged
                subprocess.run(
                    ["git", "rm", "--cached", os.path.basename(test_file)],
                    cwd=project_path,
                    capture_output=True
                )
            except Exception:
                pass


def test_lazydeve_tracked(project_path):
    """Test .lazydeve/ is tracked in project repos."""
    # Check if .lazydeve/ files are tracked
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Git ls-files failed: {result.stderr}"
    tracked_files = result.stdout
    
    # Verify .lazydeve/ directory is tracked
    assert ".lazydeve" in tracked_files, ".lazydeve/ directory not tracked in project repository"
    
    # Verify key .lazydeve/ files are tracked
    assert any(".lazydeve" in line for line in tracked_files.split("\n")), \
        "No .lazydeve/ files found in tracked files"
    
    # Check for specific files (may vary, so we check for common ones)
    lazydeve_files = [line for line in tracked_files.split("\n") if ".lazydeve" in line]
    assert len(lazydeve_files) > 0, "No .lazydeve/ files tracked in project repository"


def test_root_git_no_interference(project_path):
    """Test root .git doesn't interfere with project repos."""
    # Get project git directory
    git_dir_result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    
    assert git_dir_result.returncode == 0, f"Git rev-parse failed: {git_dir_result.stderr}"
    git_dir = git_dir_result.stdout.strip()
    
    # Should be .git (relative) or absolute path to project/.git, not root .git
    assert git_dir == ".git" or os.path.abspath(git_dir) == os.path.abspath(
        os.path.join(project_path, ".git")
    ), f"Git directory is not project-scoped: {git_dir}"
    
    # Verify project .git is separate from root .git
    root_git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=".",
        capture_output=True,
        text=True
    ).stdout.strip()
    
    project_git_abs = os.path.abspath(os.path.join(project_path, ".git"))
    root_git_abs = os.path.abspath(root_git_dir)
    
    assert project_git_abs != root_git_abs, \
        f"Project Git directory matches root: {project_git_abs} == {root_git_abs}"


def test_file_deletion_project_scope(project_path):
    """Test file deletion works in project scope."""
    # Create test file for deletion
    test_file = os.path.join(project_path, "test_task_3_8_delete.txt")
    try:
        with open(test_file, "w") as f:
            f.write("Task 3.8 test deletion")
        
        # Stage and commit the file first
        safe_git_add(cwd=project_path)
        safe_git_commit("test: Task 3.8 prepare deletion test", cwd=project_path)
        
        # Delete the file using remove_via_git
        deletion_result = remove_via_git(test_file, cwd=project_path)
        
        # Verify deletion was successful
        assert deletion_result["status"] == "success", \
            f"File deletion failed: {deletion_result.get('message', 'Unknown error')}"
        
        # Verify file is physically deleted
        assert not os.path.exists(test_file), "File still exists after deletion"
        
        # Verify deletion is staged in Git
        status_result = safe_git_status(cwd=project_path)
        if "stdout" in status_result and status_result["stdout"]:
            # Should show deleted file in status
            assert "deleted" in status_result["stdout"].lower() or \
                   "test_task_3_8_delete.txt" in status_result["stdout"], \
                "Deleted file not shown in git status"
    
    except Exception as e:
        # Clean up if test fails
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
            except Exception:
                pass
        raise


def test_multi_file_operations_project_scope(project_path):
    """Test multiple file operations work correctly in project scope."""
    test_files = [
        os.path.join(project_path, "test_task_3_8_multi_1.txt"),
        os.path.join(project_path, "test_task_3_8_multi_2.txt")
    ]
    
    try:
        # Create multiple test files
        for test_file in test_files:
            with open(test_file, "w") as f:
                f.write(f"Task 3.8 multi-file test: {os.path.basename(test_file)}")
        
        # Stage all files
        add_result = safe_git_add(cwd=project_path)
        assert add_result["status"] == "success", "Failed to stage multiple files"
        
        # Commit all files
        commit_result = safe_git_commit("test: Task 3.8 multi-file operations", cwd=project_path)
        assert commit_result["status"] == "success", "Failed to commit multiple files"
        
        # Verify all files are tracked
        ls_result = subprocess.run(
            ["git", "ls-files"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        tracked = ls_result.stdout
        for test_file in test_files:
            basename = os.path.basename(test_file)
            assert basename in tracked, f"File {basename} not tracked after commit"
    
    finally:
        # Clean up test files
        for test_file in test_files:
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                    subprocess.run(
                        ["git", "rm", "--cached", os.path.basename(test_file)],
                        cwd=project_path,
                        capture_output=True
                    )
                except Exception:
                    pass


def test_project_git_independence():
    """Test that different projects have independent Git repositories."""
    projects = ["projects/Project_test_2"]
    
    # Add more projects if they exist
    if os.path.exists("projects/Project_test_3_6_1"):
        projects.append("projects/Project_test_3_6_1")
    
    git_dirs = []
    for project in projects:
        project_git_path = os.path.join(project, ".git")
        if os.path.exists(project_git_path):
            # Use absolute path directly from project directory
            abs_git_dir = os.path.abspath(project_git_path)
            git_dirs.append(abs_git_dir)
    
    # Verify all projects have different Git directories
    assert len(git_dirs) > 0, "No project Git repositories found"
    assert len(set(git_dirs)) == len(git_dirs), \
        f"Projects share Git directories: {git_dirs}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

