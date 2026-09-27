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

# Unset AWS region environment variables to reproduce the issue in a cloud env without region config
for var in ["AWS_DEFAULT_REGION", "AWS_REGION"]:
    if var in os.environ:
        del os.environ[var]

try:
    from strands.vended_memory_stores import BedrockKnowledgeBaseStore
except ImportError as e:
    print(f"Failed to import BedrockKnowledgeBaseStore: {e}", file=sys.stderr)
    sys.exit(1)

try:
    store = BedrockKnowledgeBaseStore(
        name="user-memory",
        description="Personal memories about the user",
        scope="user-123",
        writable=True,
        config={
            "knowledge_base_id": "ABCDEFGHIJ",
            "data_source_type": "S3",
            "data_source_id": "DATASOURCE123",
            "s3": {
                "bucket": "my-bucket",
                "prefix": "memories/",
            },
        },
    )
except Exception as e:
    print_stacktrace(e)
    # We expect NoRegionError if the issue is present, so trigger assertion failure to indicate reproducing issue
    raise AssertionError("BedrockKnowledgeBaseStore fails with NoRegionError when region is not set.") from e

print("BedrockKnowledgeBaseStore succeeded without NoRegionError, issue appears fixed.")
sys.exit(0)
```
