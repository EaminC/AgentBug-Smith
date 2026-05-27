import os
import unittest
from unittest.mock import patch, MagicMock

import mle.model as model_module


class TestLoadModelReturnsCorrectInstance(unittest.TestCase):
    def setUp(self):
        patcher = patch("mle.model.get_config")
        self.mock_get_config = patcher.start()
        self.addCleanup(patcher.stop)

    def test_load_model_openai_returns_openai_model(self):
        self.mock_get_config.return_value = {
            'platform': model_module.MODEL_OPENAI,
            'api_key': 'dummy_api_key'
        }
        model_instance = model_module.load_model("dummy_dir")
        self.assertIsInstance(model_instance, model_module.OpenAIModel)

    def test_load_model_claude_returns_claude_model(self):
        self.mock_get_config.return_value = {
            'platform': model_module.MODEL_CLAUDE,
            'api_key': 'dummy_api_key'
        }
        model_instance = model_module.load_model("dummy_dir")
        self.assertIsInstance(model_instance, model_module.ClaudeModel)

    def test_load_model_ollama_returns_ollama_model(self):
        self.mock_get_config.return_value = {
            'platform': model_module.MODEL_OLLAMA,
            'api_key': 'dummy_api_key'
        }
        # Patch importlib.util.find_spec to pretend ollama package is installed
        with patch("mle.model.importlib.util.find_spec", return_value=True):
            model_instance = model_module.load_model("dummy_dir")
        self.assertIsInstance(model_instance, model_module.OllamaModel)

    def test_load_model_mistral_returns_mistral_model(self):
        self.mock_get_config.return_value = {
            'platform': model_module.MODEL_MISTRAL,
            'api_key': 'dummy_api_key'
        }
        # Patch importlib.util.find_spec and importlib.import_module to avoid import errors for Mistral
        with patch("mle.model.importlib.util.find_spec", return_value=True), \
             patch("mle.model.importlib.import_module") as mock_import_module:
            mock_import_module.return_value.Mistral = MagicMock()
            model_instance = model_module.load_model("dummy_dir")
        self.assertIsInstance(model_instance, model_module.MistralModel)

    def test_load_model_deepseek_returns_deepseek_model(self):
        self.mock_get_config.return_value = {
            'platform': model_module.MODEL_DEEPSEEK,
            'api_key': 'dummy_api_key'
        }
        model_instance = model_module.load_model("dummy_dir")
        self.assertIsInstance(model_instance, model_module.DeepSeekModel)

    def test_load_model_unknown_platform_returns_none(self):
        self.mock_get_config.return_value = {
            'platform': "unknown_platform",
            'api_key': 'dummy_api_key'
        }
        model_instance = model_module.load_model("dummy_dir")
        self.assertIsNone(model_instance)


class TestOpenAIModelBaseUrl(unittest.TestCase):
    @patch("openai.chat.completions.create")
    def test_openai_model_uses_env_base_url(self, mock_create):
        # Set environment variable for OPENAI_BASE_URL
        test_url = "https://custom.openai.api/v1"
        with patch.dict(os.environ, {"OPENAI_BASE_URL": test_url}):
            # Create OpenAIModel instance; it should pick up the env base_url
            model = model_module.OpenAIModel(api_key="dummy_key", model=None)
            # The client attribute should have a base_url attribute equal to test_url
            self.assertTrue(hasattr(model.client, "base_url"))
            # The base_url attribute is a URL object, convert to str and strip trailing slash for comparison
            base_url_str = str(model.client.base_url).rstrip("/")
            self.assertEqual(base_url_str, test_url)


if __name__ == "__main__":
    unittest.main()
