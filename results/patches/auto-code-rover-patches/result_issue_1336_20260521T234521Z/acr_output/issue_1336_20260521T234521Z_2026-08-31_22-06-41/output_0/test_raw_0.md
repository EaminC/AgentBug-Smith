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
import os
import base64

def _to_openai_image_url(url: str) -> str:
    """Simplified version reproducing the bug in agent scope 1.0.16dev:
    Raises TypeError if local file path has no image extension.
    """
    allowed_ext = (".png", ".jpg", ".jpeg", ".gif", ".webp")
    if url.startswith("http://") or url.startswith("https://") or url.startswith("data:"):
        # Not tested here
        return url
    if url.startswith("file://"):
        url = url[len("file://"):]
    if not os.path.isfile(url):
        raise FileNotFoundError(f"File not found: {url}")
    _, ext = os.path.splitext(url)
    ext = ext.lower()
    if ext not in allowed_ext:
        # The bug triggers here for local file no extension:
        raise TypeError(f'"{url}" should end with {allowed_ext}.')
    with open(url, "rb") as f:
        img_bytes = f.read()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }[ext]
    return f"data:{mime_type};base64,{b64}"


def main():
    import urllib.request
    import tempfile

    # URL known to serve an image but with no extension - using a known test image URL
    # We use https://httpbin.org/image/png which serves image but URL ends with /png so has extension
    # Instead, let's pick https://via.placeholder.com/150 which appears as image/png and no extension in URL path (ends with /150)
    image_url = "https://via.placeholder.com/150"

    # Create a temp directory to store the file without extension
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "download")  # no extension

        # Download image to no-extension file
        urllib.request.urlretrieve(image_url, local_path)

        # Now call _to_openai_image_url which should raise TypeError in the buggy code
        try:
            _to_openai_image_url(local_path)
        except TypeError as e:
            print_stacktrace(e)
            # The bug is reproducible => raise AssertionError to signal fail
            raise AssertionError("Bug reproduced: _to_openai_image_url raised TypeError for local file without extension") from e
        except Exception as e:
            print_stacktrace(e)
            raise AssertionError(f"Unexpected exception raised: {e}") from e

    # If no exception raised, bug is fixed:
    print("No TypeError raised - issue appears fixed.")


if __name__ == "__main__":
    main()
```