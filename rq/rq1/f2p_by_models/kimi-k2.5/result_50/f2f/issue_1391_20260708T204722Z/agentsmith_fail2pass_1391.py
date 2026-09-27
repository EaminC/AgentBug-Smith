from pathlib import Path

def test_unittest_workflow_exists():
    """Test that the unittest workflow file was added (linked to PR changes)."""
    repo_root = Path(__file__).parent.parent
    workflow_file = repo_root / ".github" / "workflows" / "unittest.yml"
    
    # This file is added by the patch - should not exist in buggy state
    assert workflow_file.exists(), "unittest.yml workflow file should exist"
    
    content = workflow_file.read_text()
    assert "Python Unittest Coverage" in content, "Workflow should have correct name"
    assert "coverage run tests/run.py" in content, "Workflow should run coverage"
