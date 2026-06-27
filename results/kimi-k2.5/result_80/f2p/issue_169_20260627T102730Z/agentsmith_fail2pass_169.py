import textwrap

from gpt_engineer.chat_to_files import to_files


def test_square_brackets_stripped_from_filename():
    """Test that filenames wrapped in square brackets have brackets removed.
    
    This tests the fix for issue #169 where GPT-3.5 outputs filenames like
    [filename.py] instead of filename.py.
    """
    chat = textwrap.dedent(
        """
    Some description here.

    [main.py]
    ```python
    print("hello")
    ```

    [utils.py]
    ```python
    def helper():
        pass
    ```
    """
    )

    workspace = {}
    to_files(chat, workspace)

    # Before the fix, these would be stored as "[main.py]" and "[utils.py]"
    # After the fix, they should be stored as "main.py" and "utils.py"
    assert "main.py" in workspace, f"Expected 'main.py' in workspace, got: {list(workspace.keys())}"
    assert "utils.py" in workspace, f"Expected 'utils.py' in workspace, got: {list(workspace.keys())}"
    assert "[main.py]" not in workspace, f"Unexpected '[main.py]' in workspace"
    assert "[utils.py]" not in workspace, f"Unexpected '[utils.py]' in workspace"
    
    # Verify content is correct
    assert workspace["main.py"] == 'print("hello")\n'
    assert workspace["utils.py"] == "def helper():\n    pass\n"


def test_internal_brackets_preserved():
    """Test that brackets not wrapping the entire filename are preserved.
    
    Filenames like [id].jsx should remain as [id].jsx because the closing bracket
    is not at the end of the filename.
    """
    chat = textwrap.dedent(
        """
    Route file.

    [id].jsx
    ```javascript
    export default function Page() { return <div>Hi</div>; }
    ```
    """
    )

    workspace = {}
    to_files(chat, workspace)

    # [id].jsx should remain as [id].jsx because the brackets don't wrap the whole name
    assert "[id].jsx" in workspace, f"Expected '[id].jsx' in workspace, got: {list(workspace.keys())}"
    assert "id].jsx" not in workspace, f"Unexpected 'id].jsx' in workspace"
    
    # Verify content is correct
    assert workspace["[id].jsx"] == 'export default function Page() { return <div>Hi</div>; }\n'
