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


import sys
import asyncio
from unittest import mock

try:
    from google import genai
    from strands.models.gemini import GeminiModel
except ImportError as e:
    print("ERROR: Could not import required modules. Are you in the correct environment?")
    print(e)
    sys.exit(1)


async def reproduce_issue():
    # Construct the ClientError as it would appear from Vertex AI 429
    error = genai.errors.ClientError(
        429,
        {"error": {"status": "RESOURCE_EXHAUSTED", "message": "Resource exhausted. Please try again later."}},
    )
    assert error.code == 429
    assert error.status == "RESOURCE_EXHAUSTED"

    model = GeminiModel(model_id="gemini-2.5-flash", client_args={"api_key": "test"})
    with mock.patch.object(genai.Client, "aio", new_callable=mock.PropertyMock) as aio:
        aio.return_value.models.generate_content_stream.side_effect = error

        # GeminiModel.stream returns an async generator
        events = model.stream([{"role": "user", "content": [{"text": "hi"}]}])
        try:
            # The issue is that this raises raw ClientError instead of ModelThrottledException
            await events.__anext__()
        except Exception as e:
            # We check the type of exception:
            from strands.exceptions import ModelThrottledException
            if isinstance(e, ModelThrottledException):
                # Issue is fixed, exit cleanly
                sys.exit(0)
            else:
                # Issue is present — print stack trace, then assert fail to signal problem
                print_stacktrace(e)
                raise AssertionError(f"Issue reproduces: got {e.__class__.__name__}, expected ModelThrottledException") from e

def main():
    try:
        asyncio.run(reproduce_issue())
    except AssertionError:
        # reproduce_issue raised AssertionError, means issue present
        sys.exit(1)
    except Exception as e:
        # Unexpected exception
        print_stacktrace(e)
        sys.exit(2)

    # If no exception raised and exit not triggered, exit zero
    sys.exit(0)


if __name__ == "__main__":
    main()
```
