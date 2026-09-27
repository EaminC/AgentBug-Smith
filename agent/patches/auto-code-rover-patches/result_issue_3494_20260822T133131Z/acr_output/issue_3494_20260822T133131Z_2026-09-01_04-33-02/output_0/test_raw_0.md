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
import tempfile
import sys

from strands.sandbox.not_a_sandbox_local_environment import NotASandboxLocalEnvironment
from strands.vended_plugins.context_offloader import FileStorage


async def main() -> None:
    host = FileStorage(tempfile.mkdtemp())
    reference = await host.store("tooluse_abc123_0", b"payload", "text/plain")
    print("store() ->", reference)

    # Test retrieve with bare filename without extension (host)
    bare_filename = reference.split("/")[-1].removesuffix(".txt")
    try:
        await host.retrieve(bare_filename)
        # If no exception, then bug is fixed for bare filename without extension at host branch
    except KeyError as error:
        print("host, no extension ->", error)
        print_stacktrace(error)
        # This error indicates the bug still present, so assert failure here
        assert False, f"Bug present at host.retrieve() bare filename without extension: {error}"

    # Create sandboxed storage
    sandboxed = host.for_sandbox(NotASandboxLocalEnvironment())
    sandbox_reference = await sandboxed.store("tooluse_abc123_1", b"payload", "text/plain")
    print("sandboxed, full path ->", (await sandboxed.retrieve(sandbox_reference))[1])

    # try retrieve with bare filename with extension (sandbox)
    sandbox_bare_filename = sandbox_reference.split("/")[-1]
    try:
        await sandboxed.retrieve(sandbox_bare_filename)
        # If no exception, then bug is fixed for bare filename with extension at sandboxed branch
    except KeyError as error:
        print("sandboxed, bare filename ->", error)
        print_stacktrace(error)
        # This error indicates the bug still present, so assert failure here
        assert False, f"Bug present at sandboxed.retrieve() bare filename with extension: {error}"

    # If both retrieve calls succeeded with bare filenames, print success
    print("\nAll tests passed: retrieve() accepts bare filenames as documented.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as e:
        sys.exit(1)
```
