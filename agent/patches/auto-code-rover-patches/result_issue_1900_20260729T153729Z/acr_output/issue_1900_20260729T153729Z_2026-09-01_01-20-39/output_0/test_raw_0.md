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

import base64
import sys

from agentscope.message import Base64Source, DataBlock
from agentscope.tool import ToolChunk, ToolResponse


def main():
    response = ToolResponse()

    response.append_chunk(
        ToolChunk(
            content=[
                DataBlock(
                    id="image",
                    source=Base64Source(
                        data=base64.b64encode(b"hello").decode("ascii"),
                        media_type="image/png",
                    ),
                ),
            ],
        ),
    )

    response.append_chunk(
        ToolChunk(
            content=[
                DataBlock(
                    id="image",
                    source=Base64Source(
                        data=base64.b64encode(b"world").decode("ascii"),
                        media_type="image/png",
                    ),
                ),
            ],
        ),
    )

    merged = response.content[0].source.data
    decoded = base64.b64decode(merged)

    try:
        # The merged base64 string should decode to b"helloworld"
        assert decoded == b"helloworld", (
            f"Base64 payload mismatch: decoded bytes {decoded} != expected b'helloworld'"
        )
    except AssertionError as e:
        print_stacktrace(e)
        # Re-raise to show failure clearly with error code 1
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
    sys.exit(0)
```
