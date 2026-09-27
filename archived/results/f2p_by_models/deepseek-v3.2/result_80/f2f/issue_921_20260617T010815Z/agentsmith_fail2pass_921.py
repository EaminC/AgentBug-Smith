import sys
import pytest
from unittest.mock import patch, MagicMock


def test_import_token_usage_without_langchain_community():
    """
    Test that token_usage can be imported when langchain.callbacks.openai_info
    does NOT have get_openai_token_cost_for_model (simulating the buggy environment).
    In buggy code, this import will fail.
    In fixed code, it will succeed because of the try/except fallback.
    """
    # Mock the import to simulate missing function
    with patch('langchain.callbacks.openai_info.get_openai_token_cost_for_model', None):
        # Force reload the module to pick up the mock
        sys.modules.pop("gpt_engineer.core.token_usage", None)
        # Now attempt to import token_usage. In buggy code, this will raise ImportError.
        # In fixed code, it will succeed because of the try/except.
        try:
            import gpt_engineer.core.token_usage
            # If we reach here, the import succeeded (fixed code).
            # The test should pass after the fix.
            assert True
        except ImportError as e:
            # In buggy code, we expect an ImportError.
            # The test should fail after the fix.
            raise AssertionError(f"Import failed in buggy environment: {e}")


def test_import_token_usage_with_langchain_community_only():
    """
    Test that token_usage can be imported when langchain.callbacks.openai_info is missing
    entirely (simulating newer langchain versions).
    This test passes only after the fix.
    """
    # Mock the entire module to simulate it's missing
    with patch.dict('sys.modules', {'langchain.callbacks.openai_info': None}):
        # Force reload the module
        sys.modules.pop("gpt_engineer.core.token_usage", None)
        try:
            import gpt_engineer.core.token_usage
            # If we reach here, the import succeeded (fixed code).
            # The test should pass after the fix.
            assert True
        except ImportError as e:
            # In buggy code, we expect an ImportError.
            # The test should fail after the fix.
            raise AssertionError(
                f"Import failed when langchain.callbacks.openai_info missing: {e}"
            )


def test_token_usage_aggregation():
    """
    Test that aggregate_openai_token_usage works with the imported function.
    This ensures the fix doesn't break the actual functionality.
    """
    # First ensure we can import the module
    import gpt_engineer.core.token_usage as token_usage_module
    
    # Check if aggregate_openai_token_usage exists in the module
    if hasattr(token_usage_module, 'aggregate_openai_token_usage'):
        aggregate_openai_token_usage = token_usage_module.aggregate_openai_token_usage
    else:
        # Try to find it in the module's namespace
        from gpt_engineer.core.token_usage import aggregate_openai_token_usage
    
    from langchain.schema import AIMessage, HumanMessage, SystemMessage

    # Create dummy messages
    messages = [
        AIMessage(content="Hello", additional_kwargs={"token_usage": {"total_tokens": 10}}),
        HumanMessage(content="Hi", additional_kwargs={"token_usage": {"total_tokens": 5}}),
        SystemMessage(content="System", additional_kwargs={"token_usage": {"total_tokens": 3}}),
    ]
    model = "gpt-3.5-turbo"
    
    # Mock the get_openai_token_cost_for_model function to avoid network calls
    with patch('gpt_engineer.core.token_usage.get_openai_token_cost_for_model') as mock_func:
        mock_func.return_value = 0.002  # Mock a cost value
        result = aggregate_openai_token_usage(messages, model)
        # The function should return a float (cost) or None if calculation fails
        # We just check that it doesn't crash.
        assert result is None or isinstance(result, (int, float))


def test_fallback_to_langchain_community():
    """
    Test that when langchain.callbacks.openai_info doesn't have the function,
    it falls back to langchain_community.callbacks.openai_info.
    """
    # Mock langchain.callbacks.openai_info to not have the function
    with patch('langchain.callbacks.openai_info.get_openai_token_cost_for_model', None):
        # Mock langchain_community to have the function
        mock_func = MagicMock(return_value=0.002)
        with patch('langchain_community.callbacks.openai_info.get_openai_token_cost_for_model', mock_func):
            # Force reload
            sys.modules.pop("gpt_engineer.core.token_usage", None)
            import gpt_engineer.core.token_usage
            
            # Now test that the function uses the fallback
            from langchain.schema import AIMessage
            messages = [AIMessage(content="Hello", additional_kwargs={"token_usage": {"total_tokens": 10}})]
            
            result = gpt_engineer.core.token_usage.aggregate_openai_token_usage(messages, "gpt-3.5-turbo")
            # Verify the mock was called
            mock_func.assert_called_once()
            assert result is not None