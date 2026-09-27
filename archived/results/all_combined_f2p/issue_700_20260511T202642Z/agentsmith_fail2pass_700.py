import pytest
from aider import models


def test_vertex_ai_claude_models_in_model_settings():
    """
    This test ensures that the vertex_ai/claude-3-5-sonnet@20240620 model
    is present in MODEL_SETTINGS after the fix.

    The buggy codebase does not include this model, so the test will fail there.
    After applying the fix, the model is included and the test should pass.
    """
    # MODEL_SETTINGS is a list of ModelSettings namedtuples or dataclasses.
    # The attribute for the model identifier is 'name' (not 'model').
    # Defensive: check MODEL_SETTINGS is not empty
    if not models.MODEL_SETTINGS:
        pytest.fail("MODEL_SETTINGS is empty, cannot test presence of vertex_ai models")

    # Check that the ModelSettings objects have attribute 'name'
    first = models.MODEL_SETTINGS[0]
    assert hasattr(first, "name"), "ModelSettings object missing 'name' attribute"

    # The buggy codebase lacks the vertex_ai/claude-3-5-sonnet@20240620 model
    # The fixed codebase includes it exactly as that string in the 'name' attribute
    model_names = [m.name for m in models.MODEL_SETTINGS]

    # The test fails if the model is not found (buggy)
    assert "vertex_ai/claude-3-5-sonnet@20240620" in model_names, (
        "vertex_ai/claude-3-5-sonnet@20240620 model not found in MODEL_SETTINGS"
    )

    # Also check the related model with @20240229 is present
    assert "vertex_ai/claude-3-opus@20240229" in model_names, (
        "vertex_ai/claude-3-opus@20240229 model not found in MODEL_SETTINGS"
    )
