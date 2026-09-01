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
        print(f'  File "{frame.filename}"')
        print(f"    {line_number}: {code_context}")
    print(f"{e.__class__.__name__}: {e}")

import sys

try:
    from strands.models.llamacpp import LlamaCppModel
except ImportError as e:
    print("Could not import LlamaCppModel from strands.models.llamacpp. Make sure you run this in the project root with dependencies installed.", file=sys.stderr)
    sys.exit(1)

def main():
    model = LlamaCppModel(model_id="test", params={
        "temperature": 0.7,     # OpenAI-standard → top level
        "top_k": 40,            # llama.cpp sampler
        "repeat_penalty": 1.1,  # llama.cpp sampler
        "mirostat": 2,          # llama.cpp sampler
    })

    req = model._format_request(messages=[{"role": "user", "content": [{"text": "hi"}]}])

    # Check presence of keys:
    try:
        assert "temperature" in req, "temperature should be top-level"
        # The bug is top_k is missing at top-level which means params nested under extra_body
        assert "top_k" in req, "top_k should be top-level, but it is nested under extra_body"
        # If top_k is top-level, the issue is fixed, so exit with code 0
    except AssertionError as e:
        print_stacktrace(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
```