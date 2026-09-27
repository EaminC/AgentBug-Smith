import pytest
from agent.utils import generate_plan_card_ascii


def test_generate_plan_card_ascii_exists_and_formats():
    """Test that generate_plan_card_ascii creates DAG-formatted output from task dicts."""
    task_dicts = {
        "tasks": [
            {
                "name": "Data Collection",
                "resources": ["scraper.py", "api_key"],
                "description": "Gather raw data from external APIs and local files"
            },
            {
                "name": "Data Processing",
                "resources": ["pandas", "numpy"],
                "description": "Clean, normalize, and transform raw data into features"
            },
            {
                "name": "Model Training",
                "resources": ["sklearn", "gpu"],
                "description": "Train classification model on processed features"
            }
        ]
    }

    result = generate_plan_card_ascii(task_dicts)

    assert isinstance(result, str)
    assert len(result) > 0
    
    # Verify task names are present in the output
    assert "Data Collection" in result
    assert "Data Processing" in result
    assert "Model Training" in result
    
    # Verify resources are listed
    assert "scraper.py" in result
    assert "pandas" in result
    
    # Verify descriptions are wrapped and present
    assert "Gather raw data" in result
    
    # Verify PrettyTable formatting (borders)
    assert "|" in result
    
    # Verify DAG arrows exist between tasks (| and V characters)
    # For 3 tasks, we expect arrows after task 1 and 2, but not after task 3
    lines = result.split('\n')
    arrow_lines = [line for line in lines if line.strip() == '|' or 'V' in line]
    assert len(arrow_lines) > 0, "Expected DAG arrows between tasks"


def test_generate_plan_card_ascii_single_task_no_arrow():
    """Test that a single task plan does not have trailing arrows."""
    task_dicts = {
        "tasks": [
            {
                "name": "Standalone Task",
                "resources": ["cpu"],
                "description": "Execute standalone operation"
            }
        ]
    }

    result = generate_plan_card_ascii(task_dicts)
    
    assert "Standalone Task" in result
    # Single task should not have the downward arrow "V" since it's the last (and only) task
    assert "V" not in result
