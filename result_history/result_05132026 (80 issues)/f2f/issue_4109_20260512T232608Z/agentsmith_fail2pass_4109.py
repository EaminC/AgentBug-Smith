import os
from aider.models import Model


def test_vertex_ai_model_name_normalization():
    # Model name that triggers the buggy behavior (contains "-language-models/")
    buggy_model_name = "vertex_ai-language-models/gemini-2.5-flash-preview-04-17"

    # Create Model instance with the buggy model name and pass API key from env
    model = Model(buggy_model_name, api_key=os.getenv("OPENAI_API_KEY"))

    # The fix normalizes the model name by replacing "-language-models/" with "/"
    expected_normalized_name = "vertex_ai/gemini-2.5-flash-preview-04-17"

    # Assert that the model.name is normalized correctly
    # On buggy code, this will fail because the name is not normalized
    # On fixed code, this will pass
    assert model.name == expected_normalized_name, (
        f"Model name was not normalized correctly. "
        f"Expected: {expected_normalized_name}, Got: {model.name}"
    )