import asyncio
import tempfile
from pathlib import Path

from strands.vended_plugins.context_offloader import FileStorage
from strands.sandbox.not_a_sandbox_local_environment import NotASandboxLocalEnvironment


async def test_filestorage_retrieve_accepts_bare_filename_and_stem():
    """Test that FileStorage.retrieve accepts bare filenames and stems as references.

    This test reproduces the bug where sandbox-bound FileStorage rejects bare filenames,
    and the retrieve method does not accept stems without extensions as promised.

    The test will fail on the buggy codebase (raises KeyError) and pass after the fix.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Host storage (no sandbox)
        host = FileStorage(tmpdir)
        # Store content and get full reference path
        reference = await host.store("tooluse_abc123_0", b"payload", "text/plain")
        # Extract bare filename (with extension)
        filename = Path(reference).name
        # Extract stem (filename without extension)
        stem = Path(reference).stem

        # Retrieve by full reference (should always succeed)
        content_full, ctype_full = await host.retrieve(reference)
        assert content_full == b"payload"
        assert ctype_full == "text/plain"

        # Retrieve by bare filename (should succeed per docstring)
        content_file, ctype_file = await host.retrieve(filename)
        assert content_file == b"payload"
        assert ctype_file == "text/plain"

        # Retrieve by stem (filename without extension) (should succeed per docstring)
        content_stem, ctype_stem = await host.retrieve(stem)
        assert content_stem == b"payload"
        assert ctype_stem == "text/plain"

        # Now test sandbox-bound storage
        sandbox = NotASandboxLocalEnvironment()
        sandboxed = host.for_sandbox(sandbox)
        sandbox_reference = await sandboxed.store("tooluse_abc123_1", b"payload2", "text/plain")
        sandbox_filename = Path(sandbox_reference).name
        sandbox_stem = Path(sandbox_reference).stem

        # Retrieve by full reference path (should succeed)
        content_sandbox_full, ctype_sandbox_full = await sandboxed.retrieve(sandbox_reference)
        assert content_sandbox_full == b"payload2"
        assert ctype_sandbox_full == "text/plain"

        # Retrieve by bare filename (should succeed after fix)
        content_sandbox_file, ctype_sandbox_file = await sandboxed.retrieve(sandbox_filename)
        assert content_sandbox_file == b"payload2"
        assert ctype_sandbox_file == "text/plain"

        # Retrieve by stem (should succeed after fix)
        content_sandbox_stem, ctype_sandbox_stem = await sandboxed.retrieve(sandbox_stem)
        assert content_sandbox_stem == b"payload2"
        assert ctype_sandbox_stem == "text/plain"


def test_run_asyncio_test():
    # Run the async test function in the event loop
    asyncio.run(test_filestorage_retrieve_accepts_bare_filename_and_stem())
