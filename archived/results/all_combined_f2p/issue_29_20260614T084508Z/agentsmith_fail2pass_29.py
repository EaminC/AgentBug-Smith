import pytest
from agent.types.step import Plan


def test_plan_has_training_entry_file_attribute():
    """Test that Plan class has training_entry_file attribute (not target)."""
    plan = Plan(
        project_name="test_project",
        project="/tmp/test",
        launch_env="local",
        current_task=1,
        lang="python",
        llm="openai",
        training_entry_file="/tmp/test/main.py",
        requirement="test requirement",
        dataset="/tmp/dataset"
    )
    assert hasattr(plan, 'training_entry_file')
    assert plan.training_entry_file == "/tmp/test/main.py"


def test_plan_has_launch_env_attribute():
    """Test that Plan class has launch_env attribute."""
    plan = Plan(
        project_name="test_project",
        project="/tmp/test",
        launch_env="local",
        current_task=1,
        lang="python",
        llm="openai",
        training_entry_file="/tmp/test/main.py",
        requirement="test requirement",
        dataset="/tmp/dataset"
    )
    assert hasattr(plan, 'launch_env')
    assert plan.launch_env == "local"


def test_plan_has_dataset_attribute():
    """Test that Plan class has dataset attribute."""
    plan = Plan(
        project_name="test_project",
        project="/tmp/test",
        launch_env="local",
        current_task=1,
        lang="python",
        llm="openai",
        training_entry_file="/tmp/test/main.py",
        requirement="test requirement",
        dataset="/tmp/dataset"
    )
    assert hasattr(plan, 'dataset')
    assert plan.dataset == "/tmp/dataset"


def test_plan_training_entry_file_optional():
    """Test that training_entry_file is optional in Plan."""
    plan = Plan(
        project_name="test_project",
        project="/tmp/test",
        launch_env="local",
        current_task=1,
        lang="python",
        llm="openai",
        requirement="test requirement"
    )
    assert hasattr(plan, 'training_entry_file')
    assert plan.training_entry_file is None


def test_plan_dataset_optional():
    """Test that dataset is optional in Plan."""
    plan = Plan(
        project_name="test_project",
        project="/tmp/test",
        launch_env="local",
        current_task=1,
        lang="python",
        llm="openai",
        requirement="test requirement"
    )
    assert hasattr(plan, 'dataset')
    assert plan.dataset is None


def test_plan_does_not_have_target_attribute():
    """Test that Plan class does not have the old 'target' attribute."""
    plan = Plan(
        project_name="test_project",
        project="/tmp/test",
        launch_env="local",
        current_task=1,
        lang="python",
        llm="openai",
        training_entry_file="/tmp/test/main.py",
        requirement="test requirement",
        dataset="/tmp/dataset"
    )
    assert not hasattr(plan, 'target')
