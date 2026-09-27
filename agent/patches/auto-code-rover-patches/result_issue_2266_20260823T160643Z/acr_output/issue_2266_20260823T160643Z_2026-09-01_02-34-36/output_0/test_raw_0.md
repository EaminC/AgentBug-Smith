```python
# reproducer.py
import asyncio
import sys
import threading
import warnings
import re

from strands.models.bedrock import BedrockModel


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


# We want to catch "Task exception was never retrieved" warnings
# These are emitted as ResourceWarning with a message containing
# "Task exception was never retrieved"
# We want to detect these and cause an AssertionError to confirm the issue reproduces.

def main():
    # Run the reproduction scenario 1: timeout on first event via asyncio.wait_for

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    caught_warnings = []

    def warning_capture(message, category, filename, lineno, file=None, line=None):
        msg_str = str(message)
        caught_warnings.append((category, msg_str, filename, lineno))

    # Register warning capture handler for warnings emitted during event loop run
    warnings.simplefilter("always", ResourceWarning)
    warnings.showwarning = warning_capture

    async def reproduce():
        model = BedrockModel()  # uses default model id
        gen = model.stream(
            messages=[{"role": "user", "content": [{"text": "hello"}]}]
        )
        ait = gen.__aiter__()
        try:
            # Set unrealistically short timeout (1ms)
            # to cause timeout before first chunk is received.
            await asyncio.wait_for(ait.__anext__(), timeout=0.001)
        except asyncio.TimeoutError:
            pass  # expected due to timeout

        # The async generator is now abandoned while the internal
        # background task keeps running. Wait enough time for
        # the internal boto3/converse_stream read_timeout to occur
        # and the exception to be set on the background task.
        await asyncio.sleep(65)

    try:
        loop.run_until_complete(reproduce())
    finally:
        loop.close()

    # Now we inspect warnings captured for "Task exception was never retrieved"
    # This warning indicates the internal async task's exception was never retrieved,
    # demonstrating the leak described in the issue.

    found_orphan_warning = False
    for category, msg_str, filename, lineno in caught_warnings:
        if (
            issubclass(category, ResourceWarning)
            and "Task exception was never retrieved" in msg_str
        ):
            found_orphan_warning = True
            print("\nDetected 'Task exception was never retrieved' warning:")
            print(f"  Warning message: {msg_str}", file=sys.stderr)
            print(f"  Location: {filename}:{lineno}", file=sys.stderr)
            break

    if found_orphan_warning:
        # The issue reproduces: the internal async task's exception was never retrieved
        # Raise AssertionError to indicate the problem presence
        raise AssertionError(
            "BedrockModel.stream internal background task exception was never retrieved. "
            "The issue is present."
        )
    else:
        print("No 'Task exception was never retrieved' warnings detected. The issue is fixed.")


if __name__ == "__main__":
    main()
```
