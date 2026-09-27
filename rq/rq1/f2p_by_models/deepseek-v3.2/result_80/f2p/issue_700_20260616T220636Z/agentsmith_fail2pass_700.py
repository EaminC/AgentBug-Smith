import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aider.models import MODEL_SETTINGS, ModelSettings


def test_vertex_ai_claude_models_in_settings():
    """Check that vertex_ai/claude-* models are present in MODEL_SETTINGS."""
    # The bug: vertex_ai/claude-* models are missing from MODEL_SETTINGS,
    # causing aider to fall back to whole-file editing with no repo map.
    # The fix adds entries for vertex_ai/claude-3-5-sonnet@20240620 and
    # vertex_ai/claude-3-opus@20240229.
    # We'll test that after the fix, these models are present and have correct settings.
    # On buggy code, these lookups will fail because the entries are missing.

    # Build a mapping from model name to ModelSettings entry
    model_map = {ms.name: ms for ms in MODEL_SETTINGS}

    # These are the two models added by the fix.
    # In buggy code, they are absent, so .get() will return None.
    sonnet_entry = model_map.get("vertex_ai/claude-3-5-sonnet@20240620")
    opus_entry = model_map.get("vertex_ai/claude-3-opus@20240229")

    # Assert they exist (fail on buggy, pass on fixed).
    assert sonnet_entry is not None, "vertex_ai/claude-3-5-sonnet@20240620 missing from MODEL_SETTINGS"
    assert opus_entry is not None, "vertex_ai/claude-3-opus@20240229 missing from MODEL_SETTINGS"

    # Verify they have the expected edit_format (should be "diff").
    assert sonnet_entry.edit_format == "diff"
    assert opus_entry.edit_format == "diff"

    # Verify they have use_repo_map=True (as per the fix).
    assert sonnet_entry.use_repo_map is True
    assert opus_entry.use_repo_map is True

    # Verify weak_model_name is set correctly.
    assert sonnet_entry.weak_model_name == "vertex_ai/claude-3-haiku@20240307"
    assert opus_entry.weak_model_name == "vertex_ai/claude-3-haiku@20240307"

    # Verify send_undo_reply is True for opus (as per the fix).
    assert opus_entry.send_undo_reply is True
    # sonnet does not have send_undo_reply set, so it should be False (default).
    assert sonnet_entry.send_undo_reply is False


if __name__ == "__main__":
    # Simple runner for standalone execution.
    try:
        test_vertex_ai_claude_models_in_settings()
        print("Test passed.")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
