from crewai.tools import tool


def test_tool_decorator_result_as_answer_flag():
    # Tool with result_as_answer=True
    @tool("Tool with result as answer", result_as_answer=True)
    def tool_with_result_as_answer(input_text: str) -> str:
        """Returns input text."""
        return input_text

    assert tool_with_result_as_answer.result_as_answer is True
    converted = tool_with_result_as_answer.to_structured_tool()
    assert converted.result_as_answer is True

    # Tool with default result_as_answer (should be False)
    @tool("Tool with default result_as_answer")
    def tool_with_default_result_as_answer(input_text: str) -> str:
        """Returns input text."""
        return input_text

    assert tool_with_default_result_as_answer.result_as_answer is False
    converted_default = tool_with_default_result_as_answer.to_structured_tool()
    assert converted_default.result_as_answer is False
