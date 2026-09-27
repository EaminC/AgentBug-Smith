import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# 1. Ensure live workspace source (/app/src) is prioritized
src_dir = str(Path("/app/src").resolve())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 2. Mock mcp module to prevent agentscope top-level import conflicts
mock_mcp = MagicMock()
mock_mcp.__path__ = []

sys.modules["mcp"] = mock_mcp
sys.modules["mcp.types"] = MagicMock()
sys.modules["mcp.client"] = MagicMock()
sys.modules["mcp.client.session"] = MagicMock()
sys.modules["mcp.client.streamable_http"] = MagicMock()
sys.modules["mcp.client.sse"] = MagicMock()
sys.modules["mcp.client.stdio"] = MagicMock()

# 3. Import function under test
from agentscope.formatter._openai_formatter import _to_openai_image_url


def test_to_openai_image_url_with_local_file_no_extension():
    """
    Issue #1336 / PR #1341:
    When a local image file has no extension, _to_openai_image_url must
    detect the image type using filetype rather than raising TypeError.
    """
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f"
        b"\x15\xc4\x89\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd"
        b"\x8d\x18\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "downloaded_image_no_ext")
        with open(file_path, "wb") as f:
            f.write(png_bytes)

        # Before fix: raises TypeError ("... should end with (.png, .jpg, ...)") -> FAILS
        # After fix: detected as image/png -> PASSES
        result = _to_openai_image_url(file_path)
        assert result.startswith("data:image/png;base64,")


def test_to_openai_image_url_with_file_url_scheme_no_extension():
    """Verify file:// URI scheme without file extension."""
    gif_bytes = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
        b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "downloaded_gif_no_ext")
        with open(file_path, "wb") as f:
            f.write(gif_bytes)

        file_url = f"file://{file_path}"
        result = _to_openai_image_url(file_url)
        assert result.startswith("data:image/gif;base64,")