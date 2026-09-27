import os
import base64
import tempfile
import pytest
from agentscope.formatter._openai_formatter import _to_openai_image_url


def test_to_openai_image_url_with_local_file_no_extension():
    # Create a temporary image file without extension
    # Use a small valid PNG image binary content
    png_header = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f"
        b"\x15\xc4\x89\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd"
        b"\x8d\x18\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "imagefile")  # no extension
        with open(file_path, "wb") as f:
            f.write(png_header)

        # Call the function under test
        result = _to_openai_image_url(file_path)
        assert result.startswith("data:image/png;base64,")


def test_to_openai_image_url_raises_type_error_for_non_image_file():
    # Create a temporary non-image file without extension
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "notimage")
        with open(file_path, "w") as f:
            f.write("this is not an image")

        # The function should raise ValueError for non-image files without extension
        with pytest.raises(ValueError):
            _to_openai_image_url(file_path)


def test_to_openai_image_url_with_file_url_scheme_no_extension():
    # Create a temporary image file without extension
    gif_header = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
        b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "imagefile")  # no extension
        with open(file_path, "wb") as f:
            f.write(gif_header)

        file_url = f"file://{file_path}"
        result = _to_openai_image_url(file_url)
        assert result.startswith("data:image/gif;base64,")
