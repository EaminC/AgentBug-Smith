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


def main():
    import subprocess
    import time
    import sys
    import os

    # Run mcp_managed_client.py which sets up MCPClient but does NOT call agent (the hanging case)
    # The script "mcp_managed_client.py" contains the hanging example in its main, so call it as subprocess.

    # Use Python executable and exact filename
    command = [sys.executable, "mcp_managed_client.py"]

    # Run with a timeout to detect hanging
    # After printing "DONE", the script hangs if bug is present.

    # We check output line by line, and we want to see "DONE"
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except Exception as e:
        print(f"ERROR: Failed to run subprocess: {e}", file=sys.stderr)
        raise

    done_seen = False
    try:
        for line in proc.stdout:
            print(line, end="")  # echo output
            if "DONE" in line:
                done_seen = True
                break  # We found DONE line, expect the process to exit soon
    except Exception as e:
        print(f"ERROR: Exception while reading output: {e}", file=sys.stderr)
        raise

    # Wait shortly for process to exit
    try:
        ret = proc.wait(timeout=3)
    except subprocess.TimeoutExpired as e:
        # Process didn't exit and hangs
        proc.kill()
        proc.wait()
        # Compose AssertionError and print stack trace to indicate hanging issue
        import traceback

        e2 = AssertionError(
            "Detected hanging on exit of mcp_managed_client.py subprocess"
            " - does not exit after printing DONE within timeout."
        )
        print_stacktrace(e2)
        raise e2

    if not done_seen:
        e2 = AssertionError(
            "Did not observe 'DONE' output from subprocess - unexpected output or hang."
        )
        print_stacktrace(e2)
        raise e2

    # If we get here, the process exited normally after printing DONE.
    # We consider that the bug is fixed.
    print("No hanging detected; MCPClient exited cleanly.")


if __name__ == "__main__":
    main()
```
