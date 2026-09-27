```python
# reproducer.py
import os
import sys

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


def run_test():
    """
    This reproducer assumes the ~/.aws/config has a non-US region set as default.
    It runs the SDK call with AWS_REGION environment variable override.
    It expects the call to succeed. If it fails due to invalid model region conflict,
    it raises AssertionError to signal the bug reproduction.
    """
    import strands.models.bedrock as bedrock

    # Model identifier from description (us region model)
    model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"

    # Use AWS_REGION envvar override as mentioned in issue
    # We simulate the usage of AWS_REGION env override here
    # We do this by forcing environment variable inside this python process
    os.environ["AWS_REGION"] = "us-west-2"

    try:
        client = bedrock.client()
        # Calling ConverseStream operation with a model id that is region-specific
        # This should respect AWS_REGION envvar, not ~/.aws/config region
        response = client.converse_stream(modelId=model_id)
        # If response is obtained, we expect no error
        # So the issue is fixed if no exception is raised
        print("Test passed: ConverseStream call succeeded with AWS_REGION override.")
        sys.exit(0)

    except Exception as e:
        # Check if it is the known ValidationException with invalid model id error from the issue
        # This indicates AWS_REGION envvar was ignored and region from config applied instead
        import botocore.errorfactory
        is_validation_exception = isinstance(e, botocore.exceptions.ClientError) and \
                                  e.response.get("Error", {}).get("Code") == "ValidationException"
        if is_validation_exception or "ValidationException" in str(e):
            print_stacktrace(e)
            raise AssertionError(
                "AWS_REGION envvar was ignored when ~/.aws/config region was set. Issue reproduces."
            ) from e
        else:
            # unexpected error, print stacktrace anyway and raise
            print_stacktrace(e)
            raise


if __name__ == "__main__":
    run_test()
```
