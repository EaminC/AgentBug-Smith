import os
import unittest
from unittest.mock import patch, MagicMock

from gpt_engineer.core import ai


class TestAzureDeploymentNameBug(unittest.TestCase):
    @patch("gpt_engineer.core.ai.AzureChatOpenAI")
    def test_azure_chat_openai_version_and_deployment_name(self, mock_azure_chat_openai):
        """
        This test verifies that when creating an AzureChatOpenAI instance,
        the openai_api_version defaults to "2024-05-01-preview" (not the old "2023-05-15"),
        and the deployment_name is correctly set from model_name.

        The buggy code uses the wrong default API version, which leads to errors.
        After the fix, the correct API version is used and no error should occur.
        """

        # Setup environment variable to None to test default behavior
        if "OPENAI_API_VERSION" in os.environ:
            del os.environ["OPENAI_API_VERSION"]

        # Create an instance of AI with azure_endpoint set and model_name set
        test_model_name = "test-deployment-name"
        test_azure_endpoint = "https://fake-azure-endpoint.openai.azure.com/"

        # Patch the AzureChatOpenAI constructor to just record parameters
        # We do not mock the _create_chat_model method itself, only the internal AzureChatOpenAI call
        # so that the real method runs and calls the patched constructor.

        # Create AI instance with azure_endpoint and model_name set
        ai_instance = ai.AI(
            model_name=test_model_name,
            azure_endpoint=test_azure_endpoint,
        )

        # Call the method that creates the chat model
        _ = ai_instance._create_chat_model()

        # Check that AzureChatOpenAI was called once
        self.assertTrue(mock_azure_chat_openai.called, "AzureChatOpenAI was not called")

        # Extract the call arguments to AzureChatOpenAI
        call_args, call_kwargs = mock_azure_chat_openai.call_args

        # Check that the deployment_name is set to model_name (not mixed or missing)
        self.assertEqual(
            call_kwargs.get("deployment_name"),
            test_model_name,
            "deployment_name should be set to model_name",
        )

        # Check that the openai_api_version is the fixed default "2024-05-01-preview"
        self.assertEqual(
            call_kwargs.get("openai_api_version"),
            "2024-05-01-preview",
            "openai_api_version should default to '2024-05-01-preview'",
        )

        # Check that openai_api_type is "azure"
        self.assertEqual(
            call_kwargs.get("openai_api_type"),
            "azure",
            "openai_api_type should be 'azure'",
        )

        # Check that streaming is passed as is (default False)
        self.assertIn("streaming", call_kwargs)


if __name__ == "__main__":
    unittest.main()
