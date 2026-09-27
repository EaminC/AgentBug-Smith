```python
# reproducer.py
import threading
import time
import requests
import traceback
import sys

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


# The quickstart orchestrator agent runs by default on localhost:3500 (Dapr default HTTP port)
# and the orchestrator service listens on http://localhost:3501 (Dapr gRPC default port usually)
# From the quickstart repo, likely the agent HTTP server is http://localhost:3500 or custom 3501
# We will try to post to the orchestrator HTTP API to start workflows.
#
# Note: The orchestrator quickstart API endpoint is usually "/orchestrator" or "/start".
# Based on the repo, the start endpoint is at /orchestrator/start, or we can inspect the main.py.
#
# For the purpose of reproducing the issue, we will:
# - Start workflow run 1 via HTTP API
# - Shortly after, start workflow run 2 via HTTP API
# - Because the issue states only one active run at a time, the 2nd request will block or delay
#
# We will measure the time of the calls and assert if the 2nd run waited for the first to finish
# indicating serialization instead of concurrency.

ORCHESTRATOR_START_URL = "http://localhost:3500/orchestrator/start"

# These parameters may require adjustments if orchestrator expects specific payload:
# From the quickstart, usually something like {"input": {"sleep": 5}} to simulate long running

def start_workflow_run(run_id: int, results: dict):
    """Starts a workflow run via POST and records the time it took to complete."""
    try:
        payload = {
            "input": {
                "run_id": run_id,
                "sleep": 5  # To simulate a long-running task (5 seconds sleep)
            }
        }
        start_time = time.perf_counter()
        r = requests.post(ORCHESTRATOR_START_URL, json=payload, timeout=20)
        end_time = time.perf_counter()
        results[run_id] = {
            "status_code": r.status_code,
            "response": r.json() if 'application/json' in r.headers.get('Content-Type', '') else r.text,
            "duration": end_time - start_time,
        }
    except Exception as e:
        results[run_id] = {
            "exception": e,
        }

def main():
    # We run two workflow runs nearly concurrently
    results = {}
    thread1 = threading.Thread(target=start_workflow_run, args=(1, results))
    thread2 = threading.Thread(target=start_workflow_run, args=(2, results))

    thread1.start()
    # slight delay to simulate close concurrency but not identical
    time.sleep(0.1)
    thread2.start()

    thread1.join()
    thread2.join()

    # Check for exceptions
    for run_id, result in results.items():
        if "exception" in result:
            print(f"Run {run_id} raised exception:")
            print_stacktrace(result["exception"])
            raise result["exception"]

    # Both should succeed with http 200
    for run_id, result in results.items():
        assert result["status_code"] == 200, f"Run {run_id} failed with status {result['status_code']} and response {result['response']}"

    # Now check durations:
    # Because each run sleeps 5 seconds inside the workflow,
    # run1 duration should be ~5 sec or more (due to processing),
    # run2 duration should also start quickly if concurrency allowed,
    # but if run2 is blocked waiting, will be about run1 + run2 duration (~10 sec).

    d1 = results[1]["duration"]  # duration of run1
    d2 = results[2]["duration"]  # duration of run2

    # We'll print the durations for user info
    print(f"Run 1 duration: {d1:.2f} sec")
    print(f"Run 2 duration: {d2:.2f} sec")

    # Check if run2 waited for run1 to complete before starting:
    # If there's concurrency, run2 duration should be about 5 sec (similar to run1)
    # If serialized, run2 duration ~ (5 + 5 sec) = 10 or more

    # Let's be conservative and say if run2 duration > 8 sec, then serial issue present
    # This threshold can catch blocking.

    if d2 > 8.0:
        # Issue present: 2nd workflow blocked until first completed
        err = AssertionError(
            "Orchestrator agent only allows one active run at a time: "
            f"second run took {d2:.2f}s, indicating it waited for the first run (took {d1:.2f}s)."
        )
        print_stacktrace(err)
        raise err

    # If we reach this, assume concurrency is working:
    print("No issue detected: multiple runs processed concurrently.")

if __name__ == "__main__":
    main()
```
