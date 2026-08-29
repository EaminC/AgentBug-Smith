from crewai.a2a.config import A2AConfig


def test_a2a_config_accepts_trust_remote_completion_status():
    """Test that A2AConfig accepts trust_remote_completion_status parameter.
    
    This test verifies the fix for issue #3899 where A2A server ignores
    'completed' status from remote agents, causing infinite delegation loops.
    
    Before the fix: A2AConfig does not accept trust_remote_completion_status,
    causing a ValidationError when trying to instantiate with this parameter.
    
    After the fix: A2AConfig accepts the parameter and respects it to return
    results directly when remote agents signal completion.
    """
    # Should be able to create config with trust_remote_completion_status=True
    config = A2AConfig(
        endpoint="http://test.example.com",
        trust_remote_completion_status=True
    )
    
    # Verify the attribute exists and is set correctly
    assert config.trust_remote_completion_status is True
    
    # Verify default is False (backward compatible behavior)
    config_default = A2AConfig(endpoint="http://test.example.com")
    assert config_default.trust_remote_completion_status is False
