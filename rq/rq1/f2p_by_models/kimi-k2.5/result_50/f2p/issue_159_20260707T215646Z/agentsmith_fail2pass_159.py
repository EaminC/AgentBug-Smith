import json
from unittest.mock import MagicMock, patch


def test_clarify_dataset_method_exists_and_handles_blur_input():
    """
    Test that AdviseAgent has clarify_dataset method that:
    1. Checks if dataset name is blur/unclear
    2. Suggests alternatives when unclear
    3. Returns user selection

    This test verifies the fix for issue #159 where agent could not
    understand blur dataset names.
    """
    # Patch get_config to avoid NoneType error during AdviseAgent initialization
    with patch('mle.agents.advisor.get_config', return_value={}):
        from mle.agents.advisor import AdviseAgent
        
        # Setup mock model with responses for the two queries
        mock_model = MagicMock()
        mock_model.query.side_effect = [
            "No",  # First query: dataset is unclear/blur
            json.dumps({
                "datasets": ["iris", "wine", "boston_housing"],
                "reason": "Standard ML datasets matching the description"
            })
        ]

        # Setup mock console with status context manager
        mock_console = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=None)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_console.status.return_value = mock_context

        # Create agent instance
        agent = AdviseAgent(mock_model, mock_console)

        # Verify method exists (fails on buggy code where method is missing)
        assert hasattr(agent, 'clarify_dataset'), "AdviseAgent should have clarify_dataset method"

        # Mock questionary to simulate user selecting "iris"
        with patch('mle.agents.advisor.questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = "iris"
            
            # Call the method with a blur/unclear dataset description
            result = agent.clarify_dataset("some flowers data")
            
            # Verify the selected dataset is returned
            assert result == "iris", "Should return the dataset selected by user"
            
            # Verify model was queried twice (once for verification, once for suggestions)
            assert mock_model.query.call_count == 2
            
            # Verify questionary was called with the suggested datasets
            mock_select.assert_called_once()
            call_args = mock_select.call_args
            assert 'choices' in call_args.kwargs
            assert call_args.kwargs['choices'] == ["iris", "wine", "boston_housing"]
