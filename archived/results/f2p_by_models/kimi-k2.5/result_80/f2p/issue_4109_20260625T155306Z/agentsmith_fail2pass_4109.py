import yaml
from pathlib import Path


def test_vertex_ai_model_settings_no_malformed_prefix():
    """Verify that Vertex AI model names don't contain the malformed 'vertex_ai-anthropic_models/' prefix."""
    settings_path = Path(__file__).parent.parent / "aider" / "resources" / "model-settings.yml"
    
    with open(settings_path, 'r') as f:
        settings = yaml.safe_load(f)
    
    malformed_entries = []
    
    for entry in settings:
        if not isinstance(entry, dict):
            continue
            
        # Check name field
        name = entry.get('name', '')
        if 'vertex_ai-anthropic_models/' in name:
            malformed_entries.append(f"name: {name}")
            
        # Check weak_model_name field  
        weak_model = entry.get('weak_model_name', '')
        if 'vertex_ai-anthropic_models/' in weak_model:
            malformed_entries.append(f"weak_model_name: {weak_model}")
            
        # Check editor_model_name field
        editor_model = entry.get('editor_model_name', '')
        if 'vertex_ai-anthropic_models/' in editor_model:
            malformed_entries.append(f"editor_model_name: {editor_model}")
    
    assert len(malformed_entries) == 0, \
        f"Found malformed Vertex AI model entries with 'vertex_ai-anthropic_models/' prefix: {malformed_entries}"
