import pytest
import strands


@pytest.mark.asyncio
async def test_docstring_description_extraction():
    """Test that docstring descriptions are extracted correctly, excluding Args section."""

    @strands.tool
    def tool_with_full_docstring(param1: str, param2: int) -> str:
        """This is the main description.

        This is more description text.

        Args:
            param1: First parameter
            param2: Second parameter

        Returns:
            A string result

        Raises:
            ValueError: If something goes wrong
        """
        return f"{param1} {param2}"

    spec = tool_with_full_docstring.tool_spec
    assert (
        spec["description"]
        == """This is the main description.

This is more description text.

Returns:
    A string result

Raises:
    ValueError: If something goes wrong"""
    )


def test_docstring_args_variations():
    """Test that various Args section formats are properly excluded."""

    @strands.tool
    def tool_with_args(param: str) -> str:
        """Main description.

        Args:
            param: Parameter description
        """
        return param

    @strands.tool
    def tool_with_arguments(param: str) -> str:
        """Main description.

        Arguments:
            param: Parameter description
        """
        return param

    @strands.tool
    def tool_with_parameters(param: str) -> str:
        """Main description.

        Parameters:
            param: Parameter description
        """
        return param

    @strands.tool
    def tool_with_params(param: str) -> str:
        """Main description.

        Params:
            param: Parameter description
        """
        return param

    for tool in [tool_with_args, tool_with_arguments, tool_with_parameters, tool_with_params]:
        spec = tool.tool_spec
        assert spec["description"] == "Main description."


def test_docstring_no_args_section():
    """Test docstring extraction when there's no Args section."""

    @strands.tool
    def tool_no_args(param: str) -> str:
        """This is the complete description.

        Returns:
            A string result
        """
        return param

    spec = tool_no_args.tool_spec
    expected_desc = """This is the complete description.

Returns:
    A string result"""
    assert spec["description"] == expected_desc


def test_docstring_only_args_section():
    """Test docstring extraction when there's only an Args section."""

    @strands.tool
    def tool_only_args(param: str) -> str:
        """Args:
        param: Parameter description
        """
        return param

    spec = tool_only_args.tool_spec
    # Should fall back to function name when no description remains
    assert spec["description"] == "tool_only_args"


def test_docstring_empty():
    """Test docstring extraction when docstring is empty."""

    @strands.tool
    def tool_empty_docstring(param: str) -> str:
        return param

    spec = tool_empty_docstring.tool_spec
    # Should fall back to function name
    assert spec["description"] == "tool_empty_docstring"


def test_docstring_preserves_other_sections():
    """Test that non-Args sections are preserved in the description."""

    @strands.tool
    def tool_multiple_sections(param: str) -> str:
        """Main description here.

        Args:
            param: This should be excluded

        Returns:
            This should be included

        Raises:
            ValueError: This should be included

        Examples:
            This should be included

        Note:
            This should be included
        """
        return param

    spec = tool_multiple_sections.tool_spec
    description = spec["description"]

    # Should include main description and other sections
    assert "Main description here." in description
    assert "Returns:" in description
    assert "This should be included" in description
    assert "Raises:" in description
    assert "Examples:" in description
    assert "Note:" in description

    # Should exclude Args section
    assert "This should be excluded" not in description
