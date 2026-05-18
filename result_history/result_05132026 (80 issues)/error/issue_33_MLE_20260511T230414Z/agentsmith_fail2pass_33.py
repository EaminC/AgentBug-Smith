import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from agent.function.chain import Chain
from agent.utils.files import read_csv_file


class TestChainTaskModelArchConfirmation(unittest.TestCase):
    def setUp(self):
        # Setup a temporary directory to simulate a project environment
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = self.temp_dir.name

        # Patch config.read to simulate project config with path
        patcher_config = patch('agent.utils.config.read')
        self.mock_config_read = patcher_config.start()
        self.addCleanup(patcher_config.stop)
        self.mock_config_read.return_value = {'project': {'path': self.project_path}}

        # Patch os.path.exists to simulate project plan file presence
        patcher_exists = patch('os.path.exists')
        self.mock_exists = patcher_exists.start()
        self.addCleanup(patcher_exists.stop)
        # Return True for project plan file path, False otherwise
        def exists_side_effect(path):
            if path.endswith('project.yml'):
                return True
            if path.startswith(self.project_path):
                return True
            return False
        self.mock_exists.side_effect = exists_side_effect

        # Patch Chain.load_plan and Chain.load_model to avoid actual file loading
        patcher_load_plan = patch('agent.function.chain.load_plan')
        self.mock_load_plan = patcher_load_plan.start()
        self.addCleanup(patcher_load_plan.stop)
        self.mock_load_plan.return_value = MagicMock()

        patcher_load_model = patch('agent.function.chain.load_model')
        self.mock_load_model = patcher_load_model.start()
        self.addCleanup(patcher_load_model.stop)
        self.mock_load_model.return_value = MagicMock()

        # Patch questionary to simulate user inputs
        patcher_questionary_text = patch('questionary.text')
        self.mock_questionary_text = patcher_questionary_text.start()
        self.addCleanup(patcher_questionary_text.stop)

        patcher_questionary_confirm = patch('questionary.confirm')
        self.mock_questionary_confirm = patcher_questionary_confirm.start()
        self.addCleanup(patcher_questionary_confirm.stop)

        # Patch req_based_generator to simulate responses from prompts
        patcher_req_based_generator = patch('agent.function.chain.req_based_generator')
        self.mock_req_based_generator = patcher_req_based_generator.start()
        self.addCleanup(patcher_req_based_generator.stop)

        # Patch plan_generator to simulate task plan generation
        patcher_plan_generator = patch('agent.function.chain.plan_generator')
        self.mock_plan_generator = patcher_plan_generator.start()
        self.addCleanup(patcher_plan_generator.stop)

        # Patch Chain.update_project_state to avoid file writes
        patcher_update_project_state = patch.object(Chain, 'update_project_state')
        self.mock_update_project_state = patcher_update_project_state.start()
        self.addCleanup(patcher_update_project_state.stop)

        # Patch Chain.console.log to suppress output during tests
        patcher_console_log = patch.object(Chain, 'console', create=True)
        self.mock_console = patcher_console_log.start()
        self.addCleanup(patcher_console_log.stop)
        self.mock_console.log = MagicMock()
        self.mock_console.status = MagicMock()
        self.mock_console.status.return_value.__enter__.return_value = None
        self.mock_console.status.return_value.__exit__.return_value = None

        # Patch read_csv_file to return a sample CSV data snippet
        patcher_read_csv_file = patch('agent.integration.files.read_csv_file')
        self.mock_read_csv_file = patcher_read_csv_file.start()
        self.addCleanup(patcher_read_csv_file.stop)
        self.mock_read_csv_file.return_value = [['text', 'label'], ['I love this!', 'positive'], ['Bad movie', 'negative']]

        # Setup default mock return values for req_based_generator and plan_generator
        # Simulate data kind detection returns 'csv_data'
        def req_based_generator_side_effect(requirement, prompt, agent):
            if 'dataset_detect' in prompt:
                return 'csv_data'
            if 'dataset_select' in prompt:
                return '/path/to/dummy.csv'
            if 'task_select' in prompt:
                # Fixed code returns "Sentiment Analysis"
                return 'Sentiment Analysis'
            if 'model_select' in prompt:
                return 'DummyModel'
            return 'unknown'
        self.mock_req_based_generator.side_effect = req_based_generator_side_effect

        # Simulate plan_generator returns a plan with tasks matching the selected task
        def plan_generator_side_effect(requirement, agent, dataset, ml_task_name):
            # Return a dict with tasks list containing the ml_task_name
            return {'tasks': [{'name': ml_task_name, 'params': {}}]}
        self.mock_plan_generator.side_effect = plan_generator_side_effect

        # Simulate questionary.confirm to always confirm (yes)
        self.mock_questionary_confirm.return_value = True

        # Simulate questionary.text to provide dummy CSV path when asked
        self.mock_questionary_text.return_value = '/path/to/dummy.csv'

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_task_model_arch_confirmation(self):
        """
        This test checks that when the Chain is run with a vague requirement and no data,
        the generated task is a specific task (e.g. "Sentiment Analysis") rather than a general one.
        The buggy code returns a general task like "Tabular Task".
        The fixed code returns a specific task like "Sentiment Analysis".
        """
        # Setup Chain instance
        chain = Chain()

        # Provide a vague user requirement that should lead to sentiment analysis task if data is considered
        vague_requirement = "I want to analyze customer feedback."

        # Patch the Chain.plan to simulate initial state with no tasks and no data_kind
        chain.plan = MagicMock()
        chain.plan.requirement = vague_requirement
        chain.plan.tasks = None
        chain.plan.current_task = 0
        chain.plan.data_kind = None
        chain.plan.dataset = None
        chain.project_name = "dummy_project"
        chain.project_setting_file = os.path.join(self.project_path, 'project.yml')
        chain.entry_file = None

        # Patch agent attribute to dummy value (not used in test)
        chain.agent = MagicMock()

        # Patch gen_file_name to return a dummy file path
        chain.gen_file_name = MagicMock(return_value=os.path.join(self.project_path, 'main.py'))

        # Patch questionary.confirm to return False after first confirmation to stop the chain gracefully
        confirm_side_effects = [True, False]  # Confirm plan, then abort chain to avoid infinite loop
        self.mock_questionary_confirm.side_effect = confirm_side_effects

        # Patch questionary.text to provide the vague requirement once
        self.mock_questionary_text.side_effect = [vague_requirement, '/path/to/dummy.csv']

        # Patch Chain.update_project_state to do nothing
        self.mock_update_project_state.return_value = None

        # Patch run_command to do nothing
        with patch('agent.function.chain.run_command'):
            # Run the chain start method which contains the main loop
            # It should generate tasks and model based on the requirement and data
            with self.assertRaises(SystemExit) as cm:
                chain.start()

            # The SystemExit is expected because the chain returns after user abort

        # After running, check that the tasks generated contain the expected task name
        # The patched req_based_generator returns 'Sentiment Analysis' in fixed code,
        # so we assert that the task name is 'Sentiment Analysis'.

        # Extract the task names from chain.plan.tasks
        task_names = [task.name for task in chain.plan.tasks]

        # Assert that the task names contain 'Sentiment Analysis' (expected after fix)
        self.assertIn('Sentiment Analysis', task_names, msg="Expected 'Sentiment Analysis' task after fix.")

        # Also assert that 'Tabular Task' is not in the task names
        self.assertNotIn('Tabular Task', task_names, msg="Did not expect 'Tabular Task' task after fix.")


if __name__ == '__main__':
    unittest.main()