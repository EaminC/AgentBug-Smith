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


import asyncio
from types import SimpleNamespace

from strands.vended_plugins.context_offloader import ContextOffloader, InMemoryStorage


async def main() -> None:
    plugin = ContextOffloader(storage=InMemoryStorage())
    agent = SimpleNamespace(event_loop_metrics=SimpleNamespace(cycle_count=0))
    tool_use = {"toolUseId": "t1", "name": "retrieve_offloaded_content", "input": {"reference": "nope"}}

    try:
        async for event in plugin.retrieve_offloaded_content.stream(tool_use, {"agent": agent}):
            result = event.tool_result
            print(result)
            # Assert this marks errors as error, not success
            status = result.get("status")
            content = result.get("content")
            if status == "success" and content and isinstance(content, list):
                # check if content contains an error message string indicating failure
                text_vals = [item.get("text", "") for item in content if isinstance(item, dict)]
                if any(text.startswith("Error: reference not found") for text in text_vals):
                    raise AssertionError(
                        f"retrieve_offloaded_content returned status='success' with error content: {content}"
                    )
    except Exception as e:
        print_stacktrace(e)
        # Exit with non-zero to indicate reproducing the bug (bug present)
        import sys
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```
