```python
# reproducer.py
import asyncio
import sys
import json

def print_stacktrace(e: Exception):
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)

async def main():
    try:
        from agentscope.memory import RedisMemory
        from agentscope.message import Msg
    except ImportError as e:
        print("Make sure you run this script in the project root where agentscope is installed.")
        print_stacktrace(e)
        sys.exit(1)

    # Create RedisMemory instance with short TTL for quick test
    mem = RedisMemory(
        session_id="test-session",
        user_id="test-user",
        host="127.0.0.1",
        port=6379,
        password=None,
        key_prefix="test:",
        key_ttl=10,  # TTL 10 seconds
    )

    # Add a message to RedisMemory
    msg = Msg("user", "hello", "user")
    await mem.add(msg)

    # Wait a short moment to ensure commands have been executed
    await asyncio.sleep(0.5)

    # Now check TTL of last msg key stored by add()
    key = mem._get_message_key(msg.id)

    ttl = await mem._client.ttl(key)
    # print for reference (can be removed)
    print(f"TTL for key {key}: {ttl}")

    # Per reported bug, TTL could be -1 indicating no expiration set
    # Assert TTL > 0 to detect the bug
    assert ttl > 0, (
        "Bug detected: message key stored by RedisMemory.add() has no TTL (ttl=-1). "
        "This indicates keys leak due to pipeline SCAN race."
    )

    # If assertion passes, exit with 0 meaning issue fixed
    print("Test passed: message key has TTL set properly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)
```
