import os
import pytest


def test_data_yml_uses_csv_data():
    """
    Test that agent/hub/data.yml uses 'csv_data' instead of 'csv_table_data'.
    
    This verifies the fix in agent/hub/data.yml.
    """
    data_yml_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'hub', 'data.yml')
    
    with open(data_yml_path, 'r') as f:
        data_content = f.read()
    
    # Check that 'csv_data' is used
    assert "- \"csv_data\"" in data_content, \
        "data.yml should contain '- \"csv_data\"'"
    
    # Check that old 'csv_table_data' is not used
    assert "csv_table_data" not in data_content, \
        "data.yml should not contain 'csv_table_data'"


def test_read_csv_file_default_limit():
    """
    Test that read_csv_file has default limit of 3.
    
    This verifies the fix in agent/integration/files.py where the default limit
    was changed from None to 3.
    """
    files_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'integration', 'files.py')
    
    with open(files_path, 'r') as f:
        files_content = f.read()
    
    # Check that the function signature has limit=3
    assert "def read_csv_file(file_path, limit=3, column_only=False):" in files_content, \
        "read_csv_file should have default limit=3"


def test_prompt_task_select_mentions_data():
    """
    Test that pmpt_task_select mentions data samples.
    
    This verifies the fix in agent/utils/prompt.py where the prompt was improved
    to mention data samples.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'utils', 'prompt.py')
    
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # Find the pmpt_task_select function
    task_select_start = prompt_content.find("def pmpt_task_select():")
    assert task_select_start != -1, "pmpt_task_select function should exist"
    
    # Extract the function content (until the next def)
    task_select_end = prompt_content.find("\ndef ", task_select_start + 1)
    task_select_func = prompt_content[task_select_start:task_select_end]
    
    # Check that it mentions data samples
    assert "data samples" in task_select_func.lower(), \
        "pmpt_task_select should mention data samples"


def test_prompt_model_select_mentions_data():
    """
    Test that pmpt_model_select mentions data samples.
    
    This verifies the fix in agent/utils/prompt.py where the prompt was improved
    to mention data samples.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'utils', 'prompt.py')
    
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # Find the pmpt_model_select function
    model_select_start = prompt_content.find("def pmpt_model_select():")
    assert model_select_start != -1, "pmpt_model_select function should exist"
    
    # Extract the function content (until the next def)
    model_select_end = prompt_content.find("\ndef ", model_select_start + 1)
    model_select_func = prompt_content[model_select_start:model_select_end]
    
    # Check that it mentions data samples
    assert "data samples" in model_select_func.lower(), \
        "pmpt_model_select should mention data samples"


def test_prompt_task_select_improved_wording():
    """
    Test that pmpt_task_select has improved wording.
    
    This verifies the fix in agent/utils/prompt.py.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'utils', 'prompt.py')
    
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # Find the pmpt_task_select function
    task_select_start = prompt_content.find("def pmpt_task_select():")
    task_select_end = prompt_content.find("\ndef ", task_select_start + 1)
    task_select_func = prompt_content[task_select_start:task_select_end]
    
    # Check for improved wording
    assert "tasked with determining" in task_select_func, \
        "pmpt_task_select should have improved wording 'tasked with determining'"


def test_prompt_model_select_improved_wording():
    """
    Test that pmpt_model_select has improved wording.
    
    This verifies the fix in agent/utils/prompt.py.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'utils', 'prompt.py')
    
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # Find the pmpt_model_select function
    model_select_start = prompt_content.find("def pmpt_model_select():")
    model_select_end = prompt_content.find("\ndef ", model_select_start + 1)
    model_select_func = prompt_content[model_select_start:model_select_end]
    
    # Check for improved wording
    assert "tasked with providing" in model_select_func, \
        "pmpt_model_select should have improved wording 'tasked with providing'"


def test_cli_error_message_format():
    """
    Test that CLI error message uses CONFIG_PROJECT_FILE constant.
    
    This verifies the fix in agent/cli.py where the error message was updated.
    """
    cli_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'cli.py')
    
    with open(cli_path, 'r') as f:
        cli_content = f.read()
    
    # Check that the error message uses CONFIG_PROJECT_FILE
    assert "f\"The {CONFIG_PROJECT_FILE} does not exist in the workspace. Aborted.\"" in cli_content, \
        "CLI should use CONFIG_PROJECT_FILE constant in error message"


def test_chain_workflow_steps_in_order():
    """
    Test that chain.py has the workflow steps in the correct order.
    
    This verifies the fix for issue #33 where the workflow order was changed:
    1. User requirements understanding
    2. Data quick review
    3. Task & Model selection
    4. Plan generation
    """
    chain_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'function', 'chain.py')
    
    with open(chain_path, 'r') as f:
        chain_content = f.read()
    
    # Check that the steps are in the correct order
    step1_pos = chain_content.find("Step 1: User requirements understanding")
    step2_pos = chain_content.find("Step 2: Data quick review")
    step3_pos = chain_content.find("Step 3: Task & Model selection")
    step4_pos = chain_content.find("Step 4: Plan generation")
    
    assert step1_pos != -1, "Chain should have Step 1: User requirements understanding"
    assert step2_pos != -1, "Chain should have Step 2: Data quick review"
    assert step3_pos != -1, "Chain should have Step 3: Task & Model selection"
    assert step4_pos != -1, "Chain should have Step 4: Plan generation"
    
    # Verify order
    assert step1_pos < step2_pos, "Step 1 should come before Step 2"
    assert step2_pos < step3_pos, "Step 2 should come before Step 3"
    assert step3_pos < step4_pos, "Step 3 should come before Step 4"


def test_chain_data_before_task_model():
    """
    Test that data collection happens before task/model selection in chain.py.
    
    This is the core fix for issue #33.
    """
    chain_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'function', 'chain.py')
    
    with open(chain_path, 'r') as f:
        chain_content = f.read()
    
    # Find the positions of key sections
    data_review_pos = chain_content.find("Step 2: Data quick review")
    task_model_pos = chain_content.find("Step 3: Task & Model selection")
    
    # Data review should come before task/model selection
    assert data_review_pos < task_model_pos, \
        "Data quick review (Step 2) should come before Task & Model selection (Step 3)"


def test_chain_uses_csv_data_constant():
    """
    Test that chain.py uses 'csv_data' instead of 'csv_table_data'.
    
    This verifies the fix in agent/function/chain.py.
    """
    chain_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'function', 'chain.py')
    
    with open(chain_path, 'r') as f:
        chain_content = f.read()
    
    # Check that 'csv_data' is used
    assert "self.plan.data_kind == 'csv_data'" in chain_content, \
        "Chain should check for 'csv_data' instead of 'csv_table_data'"
    
    # Check that old 'csv_table_data' is not used
    assert "csv_table_data" not in chain_content, \
        "Chain should not use 'csv_table_data'"


def test_chain_requirement_updated_with_data_and_task():
    """
    Test that requirement is updated with data sample and ML task.
    
    This verifies the fix where the requirement is enriched with data and task info
    before model selection.
    """
    chain_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'function', 'chain.py')
    
    with open(chain_path, 'r') as f:
        chain_content = f.read()
    
    # Check that requirement is updated with dataset sample
    assert "Dataset Sample:" in chain_content, \
        "Requirement should be updated with dataset sample"
    
    # Check that requirement is updated with ML task
    assert "ML Task:" in chain_content, \
        "Requirement should be updated with ML task"


def test_chain_console_log_usage():
    """
    Test that chain.py uses console.log instead of console.print.
    
    This verifies the fix where console.print() calls were replaced with console.log().
    """
    chain_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'function', 'chain.py')
    
    with open(chain_path, 'r') as f:
        chain_content = f.read()
    
    # Count occurrences of console.print and console.log
    print_count = chain_content.count('self.console.print(')
    log_count = chain_content.count('self.console.log(')
    
    # There should be no console.print calls (or very few if any remain)
    # The fixed version should use console.log
    assert log_count > print_count, \
        "Chain should use console.log more than console.print"


def test_cli_new_command_example():
    """
    Test that CLI help message shows proper 'mle new' command example.
    
    This verifies the fix in agent/cli.py where the command example was updated.
    """
    cli_path = os.path.join(os.path.dirname(__file__), '..', 'agent', 'cli.py')
    
    with open(cli_path, 'r') as f:
        cli_content = f.read()
    
    # Check that the command example includes project_name
    assert "'mle new your_project_name'" in cli_content, \
        "CLI should show 'mle new your_project_name' as example"
