from crewai.tools import BaseTool, tool


def test_agentsmith_fail2pass_2561():
    """Test that @tool decorator correctly handles result_as_answer parameter.

    Before the fix, the @tool decorator does not accept result_as_answer.
    After the fix, it should accept result_as_answer and set it on the created tool.
    """
    # Test 1: tool with result_as_answer=True
    @tool("Tool with result as answer", result_as_answer=True)
    def my_tool_with_result_as_answer(question: str) -> str:
        """This tool will return its result as the final answer."""
        return question

    # On buggy code, result_as_answer attribute does not exist or is not set.
    # On fixed code, it should be True.
    assert my_tool_with_result_as_answer.result_as_answer is True

    # Verify the attribute persists after conversion to structured tool
    converted_tool = my_tool_with_result_as_answer.to_structured_tool()
    assert converted_tool.result_as_answer is True

    # Test 2: tool without result_as_answer (default should be False)
    @tool("Tool with default result_as_answer")
    def my_tool_with_default(question: str) -> str:
        """This tool uses the default result_as_answer value."""
        return question

    # On buggy code, result_as_answer attribute may not exist or be something else.
    # On fixed code, it should be False (default).
    assert my_tool_with_default.result_as_answer is False

    converted_tool = my_tool_with_default.to_structured_tool()
    assert converted_tool.result_as_answer is False

    # Test 3: tool with explicit result_as_answer=False
    @tool("Tool with explicit false", result_as_answer=False)
    def my_tool_explicit_false(question: str) -> str:
        """This tool explicitly sets result_as_answer to False."""
        return question

    assert my_tool_explicit_false.result_as_answer is False
    converted_tool = my_tool_explicit_false.to_structured_tool()
    assert converted_tool.result_as_answer is False

    # Test 4: ensure the tool still works as a callable via its func attribute
    result = my_tool_with_result_as_answer.func("test question")
    assert result == "test question"
    result = my_tool_with_default.func("another question")
    assert result == "another question"
    result = my_tool_explicit_false.func("explicit false")
    assert result == "explicit false"
