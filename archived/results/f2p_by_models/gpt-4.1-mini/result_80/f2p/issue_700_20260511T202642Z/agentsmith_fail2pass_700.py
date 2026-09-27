import unittest
from aider.models import MODEL_SETTINGS


class TestVertexAIClaudeModelSettings(unittest.TestCase):
    def test_vertex_ai_claude_models_in_model_settings(self):
        # The buggy codebase does not include vertex_ai/claude-3-5-sonnet@20240620
        # and vertex_ai/claude-3-opus@20240229 in MODEL_SETTINGS.
        # After the fix, these should be present with expected attributes.

        # MODEL_SETTINGS is a list of ModelSettings namedtuples or dataclasses
        # but attribute name for model string is 'name' not 'model'.
        # This test asserts presence of the new vertex_ai models by their 'name'.

        model_names = [ms.name for ms in MODEL_SETTINGS]

        # Check the exact model names added by the fix
        expected_models = {
            "vertex_ai/claude-3-5-sonnet@20240620",
            "vertex_ai/claude-3-opus@20240229",
        }

        # Assert that these models are in the MODEL_SETTINGS list
        for model in expected_models:
            self.assertIn(model, model_names)

        # Additionally, check that these models have use_repo_map=True as per patch
        for ms in MODEL_SETTINGS:
            if ms.name in expected_models:
                self.assertTrue(ms.use_repo_map)

if __name__ == "__main__":
    unittest.main()
