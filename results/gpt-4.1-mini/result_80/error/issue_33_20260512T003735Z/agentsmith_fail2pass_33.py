import os
import unittest
from unittest.mock import patch, AsyncMock
import importlib
import sys
import pathlib

class TestGPT4Option(unittest.TestCase):
    def setUp(self):
        # Ensure src is in sys.path for imports
        repo_root = pathlib.Path(__file__).parent.parent.resolve()
        src_path = str(repo_root / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_create_model_uses_custom_model_name(self):
        """
        Test that createModel uses the customModelName option if provided,
        otherwise defaults to "gpt-3.5-turbo".
        """
        try:
            chain = importlib.import_module("src.utils.chain")
        except ImportError as e:
            self.fail(f"Failed to import src.utils.chain: {e}")

        opts_default = {"customApiKey": "", "customModelName": ""}
        model_default = chain.createModel(opts_default)
        self.assertEqual(model_default.modelName, "gpt-3.5-turbo")

        opts_custom = {"customApiKey": "", "customModelName": "gpt-4"}
        model_custom = chain.createModel(opts_custom)
        self.assertEqual(model_custom.modelName, "gpt-4")

    @patch("src.pages.api.chain.startGoalAgent", new_callable=AsyncMock)
    @patch("src.pages.api.chain.createModel")
    def test_api_chain_handler_passes_custom_model_name(self, mock_create_model, mock_start_goal_agent):
        """
        Test that the /api/chain handler passes the customModelName to createModel.
        """
        import asyncio
        from src.pages.api import chain as chain_api_module

        mock_start_goal_agent.return_value.text = "[\"task1\", \"task2\"]"
        mock_create_model.return_value = "model_instance"

        class FakeRequest:
            async def json(self):
                return {
                    "customApiKey": "testkey",
                    "customModelName": "gpt-4",
                    "goal": "test goal"
                }

        request = FakeRequest()

        response = asyncio.run(chain_api_module.default(request))

        mock_create_model.assert_called_once_with({"customApiKey": "testkey", "customModelName": "gpt-4"})

        json_data = response.json()
        self.assertIn("newTasks", json_data)
        self.assertEqual(json_data["newTasks"], ["task1", "task2"])

    @patch("src.pages.api.create.executeCreateTaskAgent", new_callable=AsyncMock)
    @patch("src.pages.api.create.createModel")
    def test_api_create_handler_passes_custom_model_name(self, mock_create_model, mock_execute_create_task_agent):
        """
        Test that the /api/create handler passes the customModelName to createModel.
        """
        import asyncio
        from src.pages.api import create as create_api_module

        mock_execute_create_task_agent.return_value.text = "[\"taskA\", \"taskB\"]"
        mock_create_model.return_value = "model_instance"

        class FakeRequest:
            async def json(self):
                return {
                    "customApiKey": "key123",
                    "customModelName": "gpt-4",
                    "goal": "goalX",
                    "tasks": ["task1"],
                    "lastTask": "last",
                    "result": "result"
                }

        request = FakeRequest()

        response = asyncio.run(create_api_module.default(request))

        mock_create_model.assert_called_once_with({
            "customApiKey": "key123",
            "customModelName": "gpt-4"
        })

        json_data = response.json()
        self.assertIn("newTasks", json_data)
        self.assertEqual(json_data["newTasks"], ["taskA", "taskB"])

    @patch("src.pages.api.execute.executeTaskAgent", new_callable=AsyncMock)
    @patch("src.pages.api.execute.createModel")
    def test_api_execute_handler_passes_custom_model_name(self, mock_create_model, mock_execute_task_agent):
        """
        Test that the /api/execute handler passes the customModelName to createModel.
        """
        import asyncio
        from src.pages.api import execute as execute_api_module

        mock_execute_task_agent.return_value.text = "task result"
        mock_create_model.return_value = "model_instance"

        class FakeRequest:
            async def json(self):
                return {
                    "customApiKey": "keyXYZ",
                    "customModelName": "gpt-4",
                    "goal": "goalY",
                    "task": "taskZ"
                }

        request = FakeRequest()

        response = asyncio.run(execute_api_module.default(request))

        mock_create_model.assert_called_once_with({
            "customApiKey": "keyXYZ",
            "customModelName": "gpt-4"
        })

        json_data = response.json()
        self.assertIn("result", json_data)
        self.assertEqual(json_data["result"], "task result")

if __name__ == "__main__":
    unittest.main()