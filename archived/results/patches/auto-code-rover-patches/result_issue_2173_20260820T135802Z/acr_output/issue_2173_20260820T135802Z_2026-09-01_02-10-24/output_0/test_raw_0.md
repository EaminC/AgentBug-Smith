```python
# reproducer.py

def print_stacktrace(e: Exception):
    import traceback
    import sys
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    import sys
    from unittest.mock import MagicMock
    try:
        from strands.agent.conversation_manager import SlidingWindowConversationManager
        from strands.types.exceptions import ContextWindowOverflowException
    except ImportError as e:
        print("Make sure you run this script from the root of the strands project with correct environment.", file=sys.stderr)
        raise e

    manager = SlidingWindowConversationManager(window_size=4)

    agent = MagicMock()
    agent.messages = [
        {"role": "user", "content": [{"text": "Review this PR"}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "1", "name": "get_diff", "input": {}}}]},
        {"role": "user", "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": "diff data"}], "status": "success"}}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "2", "name": "get_file", "input": {}}}]},
        {"role": "user", "content": [{"toolResult": {"toolUseId": "2", "content": [{"text": "file data"}], "status": "success"}}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "3", "name": "get_tree", "input": {}}}]},
        {"role": "user", "content": [{"toolResult": {"toolUseId": "3", "content": [{"text": "tree data"}], "status": "success"}}]},
        {"role": "assistant", "content": [{"text": "Here is my review"}]},
    ]

    try:
        manager.reduce_context(agent, e=Exception("context window overflow"))
    except ContextWindowOverflowException as e:
        print_stacktrace(e)
        assert False, "reduce_context failed to trim tool-heavy conversation, reproducing the issue"
    else:
        # no exception: issue fixed
        print("reduce_context trimmed conversation successfully - issue fixed.")
        sys.exit(0)
```
