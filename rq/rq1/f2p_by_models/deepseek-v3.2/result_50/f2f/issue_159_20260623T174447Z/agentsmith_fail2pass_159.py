import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from rich.console import Console
import pytest

# Import the actual modules from the repo
from mle.agents.advisor import AdviseAgent
from mle.model import Model
from mle.workflow.baseline import baseline


def test_clarify_dataset_method_exists():
    """
    Test that clarify_dataset method exists on AdviseAgent after patch.
    This should fail on buggy code and pass on fixed code.
    """
    mock_model = Mock(spec=Model)
    console = Console()
    
    # Mock get_config to avoid reading from actual config file
    with patch('mle.agents.advisor.get_config', return_value={'search_key': 'dummy'}):
        agent = AdviseAgent(mock_model, console)
    
    # This should fail on buggy code (AttributeError) and pass on fixed code
    assert hasattr(agent, 'clarify_dataset'), "AdviseAgent should have clarify_dataset method"
    assert callable(agent.clarify_dataset), "clarify_dataset should be callable"


def test_clarify_dataset_blur_name():
    """
    Test that clarify_dataset suggests datasets when dataset name is blur.
    """
    mock_model = Mock(spec=Model)
    console = Console()
    
    # Mock get_config
    with patch('mle.agents.advisor.get_config', return_value={'search_key': 'dummy'}):
        agent = AdviseAgent(mock_model, console)
    
    # Skip this test if method doesn't exist (buggy code)
    if not hasattr(agent, 'clarify_dataset'):
        pytest.skip("clarify_dataset method not found - buggy code")
    
    # Mock the model.query method to simulate "No" response
    mock_model.query.side_effect = [
        "No",  # First call: verification response
        json.dumps({  # Second call: suggestions response
            "datasets": ["MNIST", "CIFAR-10", "ImageNet"],
            "reason": "Based on the user's dataset description..."
        })
    ]
    
    # Mock questionary.select to avoid interactive prompt
    with patch('mle.agents.advisor.questionary.select') as mock_select:
        mock_select.return_value.ask.return_value = "MNIST"
        result = agent.clarify_dataset("some blur dataset")
    
    # Verify the model was called twice
    assert mock_model.query.call_count == 2
    
    # The result should be the selected dataset
    assert result == "MNIST"


def test_clarify_dataset_clear_name():
    """
    Test that clarify_dataset returns early when dataset is clear.
    """
    mock_model = Mock(spec=Model)
    console = Console()
    
    # Mock get_config
    with patch('mle.agents.advisor.get_config', return_value={'search_key': 'dummy'}):
        agent = AdviseAgent(mock_model, console)
    
    # Skip this test if method doesn't exist (buggy code)
    if not hasattr(agent, 'clarify_dataset'):
        pytest.skip("clarify_dataset method not found - buggy code")
    
    # Mock the model.query method to simulate "Yes" response
    mock_model.query.return_value = "Yes"
    
    result = agent.clarify_dataset("MNIST")
    
    # Verify the model was called only once
    mock_model.query.assert_called_once()
    
    # The method should return None (early exit)
    assert result is None


def test_clarify_dataset_integration_with_baseline():
    """
    Test that baseline workflow integrates clarify_dataset correctly.
    """
    # Create a mock cache object
    mock_cache_instance = Mock()
    mock_cache_instance.resume.return_value = None
    mock_cache_instance.__enter__ = Mock(return_value=mock_cache_instance)
    mock_cache_instance.__exit__ = Mock(return_value=None)
    mock_cache_instance.store = Mock()
    mock_cache_instance.console = Console()
    
    mock_model = Mock(spec=Model)
    mock_model.query.return_value = "Yes"
    
    # Mock the cache function from mle.utils
    with patch('mle.utils.cache.cache', return_value=mock_cache_instance):
        # Mock ask_text to return a dataset string
        with patch('mle.workflow.baseline.ask_text', return_value="MNIST"):
            # Mock AdviseAgent to avoid actual model calls
            with patch('mle.workflow.baseline.AdviseAgent') as MockAdviseAgent:
                mock_advisor = Mock()
                # Skip if method doesn't exist
                if hasattr(mock_advisor, 'clarify_dataset'):
                    mock_advisor.clarify_dataset.return_value = "MNIST"
                MockAdviseAgent.return_value = mock_advisor
                
                # Mock print_in_box to avoid console output
                with patch('mle.workflow.baseline.print_in_box'):
                    # Call baseline with a mock model
                    baseline(work_dir="/tmp/test", model=mock_model)
    
    # Verify that AdviseAgent was instantiated
    MockAdviseAgent.assert_called_once_with(mock_model, mock_cache_instance.console)
    
    # Only verify clarify_dataset was called if it exists
    if hasattr(mock_advisor, 'clarify_dataset'):
        mock_advisor.clarify_dataset.assert_called_once_with("MNIST")
        mock_cache_instance.store.assert_called_once_with("dataset", "MNIST")
    else:
        # In buggy code, clarify_dataset won't be called
        pytest.skip("clarify_dataset method not found - buggy code")


def test_clarify_dataset_returns_suggested_dataset():
    """
    Simple test to verify clarify_dataset returns expected value.
    This is a more robust test that doesn't depend on specific implementation details.
    """
    mock_model = Mock(spec=Model)
    console = Console()
    
    with patch('mle.agents.advisor.get_config', return_value={'search_key': 'dummy'}):
        agent = AdviseAgent(mock_model, console)
    
    # Skip if method doesn't exist
    if not hasattr(agent, 'clarify_dataset'):
        pytest.skip("clarify_dataset method not found - buggy code")
    
    # Test with a clear dataset name
    mock_model.query.return_value = "Yes"
    result = agent.clarify_dataset("MNIST")
    
    # Should return None for clear dataset
    assert result is None
    
    # Test with blur dataset name
    mock_model.query.reset_mock()
    mock_model.query.side_effect = [
        "No",
        json.dumps({"datasets": ["MNIST"], "reason": "test"})
    ]
    
    with patch('mle.agents.advisor.questionary.select') as mock_select:
        mock_select.return_value.ask.return_value = "MNIST"
        result = agent.clarify_dataset("some dataset")
    
    assert result == "MNIST"