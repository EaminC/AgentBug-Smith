```python
# reproducer.py
import copy
from typing import List

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


# Simulate a minimal-ish strands environment with the minimal bug reproduction:
class OpenAIResponsesModel:
    def __init__(self, config: dict):
        # config expected to have "params" dict with a "tools" list inside
        # This is the original config the user configures, holding potentially a shared "tools" list
        self.config = config

    def _format_request(self, params: dict):
        # here the bug is that params is shallow-copied by **params, so params["tools"] list is the same list inside config["params"]["tools"]
        request = {**params}

        # The bug line: extend mutates params["tools"], which is self.config["params"]["tools"] as well
        # We simulate that it extends tools by all tool specs again on every call,
        # causing exponential growth of the list.
        # In the bug: this line is causing the mutation:
        request["tools"].extend(request["tools"])

        return request


def main():
    import sys

    # Initial tools: one "web_search" added by default + one "hello_world" user tool
    initial_tools = ["web_search", "hello_world"]
    config = {"params": {"tools": initial_tools.copy()}}

    model = OpenAIResponsesModel(config)

    print(f"Initial config params tools: {len(config['params']['tools'])} entries")

    # We run 4 calls simulating multiple agent turn calls
    for i in range(1, 5):
        # Each time call _format_request with params=self.config["params"]
        # which shares tools list
        try:
            req = model._format_request(model.config["params"])
        except Exception as e:
            print_stacktrace(e)
            sys.exit(1)

        current_tools = req["tools"]
        print(f"\n  API call #{i}: {len(current_tools)} tools (expect {len(initial_tools)}): {current_tools}")

        # Assert that we did NOT duplicate tools beyond original expected count
        try:
            # The assertion fails if the bug is present:
            assert len(current_tools) == len(initial_tools), (
                f"BUG: _format_request mutated config['params']['tools'] - expected {len(initial_tools)} tools, "
                f"got {len(current_tools)} tools"
            )
        except AssertionError as e:
            print_stacktrace(e)
            raise

    print("\nDone.")
    print("Agent output: Done.")


if __name__ == "__main__":
    main()
```
