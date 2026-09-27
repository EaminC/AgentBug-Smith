import os
import sys
import yaml
from aider.models import Model, ModelInfoManager

def test_vertex_ai_model_name_normalization():
    """Test that vertex_ai model names in model-settings.yml are normalized (no -anthropic_models/)."""
    # The patch removes "-anthropic_models/" from certain vertex_ai model names.
    # Before patch, names contain "-anthropic_models/". After patch, they do not.
    # This test reads the YAML file and checks the specific entry that is changed.
    settings_path = os.path.join(
        os.path.dirname(__file__), '..', 'aider', 'resources', 'model-settings.yml'
    )
    with open(settings_path) as f:
        data = yaml.safe_load(f)
    found = False
    for entry in data:
        name = entry.get('name', '')
        if 'vertex_ai' in name and 'claude-3-7-sonnet@20250219' in name:
            found = True
            # After patch, name should be "vertex_ai/claude-3-7-sonnet@20250219"
            # Before patch, it is "vertex_ai-anthropic_models/vertex_ai/claude-3-7-sonnet@20250219"
            assert '-anthropic_models/' not in name, f"Model name contains -anthropic_models/: {name}"
    assert found, "Expected vertex_ai/claude-3-7-sonnet@20250219 entry not found in model-settings.yml"

def test_vertex_ai_model_names_in_settings():
    """Check that all vertex_ai model names in model-settings.yml do not contain -anthropic_models/."""
    settings_path = os.path.join(
        os.path.dirname(__file__), '..', 'aider', 'resources', 'model-settings.yml'
    )
    with open(settings_path) as f:
        data = yaml.safe_load(f)
    errors = []
    for entry in data:
        name = entry.get('name', '')
        if 'vertex_ai' in name:
            if '-anthropic_models/' in name:
                errors.append(f"Model name contains -anthropic_models/: {name}")
        weak = entry.get('weak_model_name', '')
        if 'vertex_ai' in weak and '-anthropic_models/' in weak:
            errors.append(f"Weak model name contains -anthropic_models/: {weak}")
        editor = entry.get('editor_model_name', '')
        if 'vertex_ai' in editor and '-anthropic_models/' in editor:
            errors.append(f"Editor model name contains -anthropic_models/: {editor}")
    # Before patch, errors list will be non-empty.
    # After patch, errors should be empty.
    assert not errors, "\n".join(errors)

def test_vertex_ai_weak_model_normalized():
    """Test that weak_model_name for vertex_ai models is normalized (no -anthropic_models/)."""
    # Use ModelInfoManager to get model info and verify that weak_model_name and editor_model_name
    # do not contain -anthropic_models/.
    mim = ModelInfoManager()
    # The ModelInfoManager loads data from model-settings.yml.
    # We'll get the info for a model that was changed in the patch.
    info = mim.get_model_info('vertex_ai/claude-3-7-sonnet@20250219')
    assert info is not None, "Model info not found for vertex_ai/claude-3-7-sonnet@20250219"
    # Check weak_model_name
    weak = info.get('weak_model_name', '')
    if weak and 'vertex_ai' in weak:
        assert '-anthropic_models/' not in weak, f"weak_model_name contains -anthropic_models/: {weak}"
    # Check editor_model_name
    editor = info.get('editor_model_name', '')
    if editor and 'vertex_ai' in editor:
        assert '-anthropic_models/' not in editor, f"editor_model_name contains -anthropic_models/: {editor}"

def test_vertex_ai_model_instantiation():
    """Test that a Model instance can be created with a vertex_ai model name after patch."""
    # Create a Model with the name that appears in model-settings.yml after patch.
    model = Model('vertex_ai/claude-3-7-sonnet@20250219')
    # The Model constructor may apply aliases, but we just want to ensure no exception.
    # Verify that the stored name does not contain "-anthropic_models/".
    assert '-anthropic_models/' not in model.name, f"Model.name contains -anthropic_models/: {model.name}"
    # Additionally, check that the model's weak_model_name (if any) is also correct.
    mim = ModelInfoManager()
    info = mim.get_model_info(model.name)
    if info:
        weak = info.get('weak_model_name', '')
        if weak and 'vertex_ai' in weak:
            assert '-anthropic_models/' not in weak, f"weak_model_name contains -anthropic_models/: {weak}"
        editor = info.get('editor_model_name', '')
        if editor and 'vertex_ai' in editor:
            assert '-anthropic_models/' not in editor, f"editor_model_name contains -anthropic_models/: {editor}"
