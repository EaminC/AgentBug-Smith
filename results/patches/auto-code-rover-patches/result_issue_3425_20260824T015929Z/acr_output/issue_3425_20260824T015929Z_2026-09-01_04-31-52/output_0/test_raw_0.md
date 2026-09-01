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


# Minimal simulation of the streaming processing logic exhibiting the signature leak bug

import sys

def process_stream(response):
    """
    Simulate processing of response message chunks.
    We track signature accumulation bug: "state['signature']" leaks across reasoning blocks.
    """
    constructed_message = {
        "reasoningBlocks": []
    }
    state = {}
    current_block_index = None

    for chunk in response:
        if "messageStart" in chunk:
            # Reset state for new message
            state = {}
            current_block_index = None
        elif "contentBlockDelta" in chunk:
            delta = chunk["contentBlockDelta"]["delta"]
            block_idx = chunk["contentBlockDelta"]["contentBlockIndex"]
            if current_block_index != block_idx:
                # New block started
                current_block_index = block_idx
                if len(constructed_message["reasoningBlocks"]) <= block_idx:
                    # Ensure list is long enough
                    while len(constructed_message["reasoningBlocks"]) <= block_idx:
                        constructed_message["reasoningBlocks"].append({
                            "reasoningContent": {
                                "reasoningText": {
                                    "text": "",
                                    # signature is added here only on contentBlockStop incorrectly
                                }
                            }
                        })
                # Reset accumulators except signature (BUG: signature not cleared here)
                state["text"] = ""
                state["reasoningText"] = ""
                # signature accumulator is NOT cleared here: this is the core issue pointed out

            reasoning_content = delta.get("reasoningContent")
            if reasoning_content:
                if "text" in reasoning_content:
                    # accumulate text
                    state["text"] += reasoning_content["text"]
                if "signature" in reasoning_content:
                    # accumulate signature by concatenation (received in chunks)
                    state["signature"] = state.get("signature", "") + reasoning_content["signature"]
        elif "contentBlockStop" in chunk:
            block_idx = chunk["contentBlockStop"]["contentBlockIndex"]
            if block_idx is None or block_idx >= len(constructed_message["reasoningBlocks"]):
                # Defensive check
                continue

            # Finalize block
            block = constructed_message["reasoningBlocks"][block_idx]
            # assign accumulated text
            if "text" in state:
                block["reasoningContent"]["reasoningText"]["text"] = state["text"]
            # BUG: signature is not popped/cleared here, just assigned if present
            if "signature" in state:
                # This is the bug: signature is assigned but not cleared.
                block["reasoningContent"]["reasoningText"]["signature"] = state["signature"]
                # signature remains in state, so next block delta accumulates on top

            # Clear accumulators except signature (BUG)
            state.pop("text", None)
            state.pop("reasoningText", None)
            # signature remains in state - leaking across blocks

        elif "messageStop" in chunk:
            # End of message
            pass

    return constructed_message


def main():
    # This response matches minimal repro given in the issue description
    response = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"text": "first"}}, "contentBlockIndex": 0}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"signature": "SIG1"}}, "contentBlockIndex": 0}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"text": "second"}}, "contentBlockIndex": 1}},
        {"contentBlockDelta": {"delta": {"reasoningContent": {"signature": "SIG2"}}, "contentBlockIndex": 1}},
        {"contentBlockStop": {"contentBlockIndex": 1}},
        {"messageStop": {"stopReason": "end_turn"}},
    ]

    # process the stream
    constructed = process_stream(response)
    sig0 = constructed["reasoningBlocks"][0]["reasoningContent"]["reasoningText"].get("signature")
    sig1 = constructed["reasoningBlocks"][1]["reasoningContent"]["reasoningText"].get("signature")

    try:
        # Expect signatures per block exactly: SIG1 and SIG2
        # Actual buggy behavior is sig1 == SIG1SIG2 (concatenated)
        assert sig0 == "SIG1", f"Block 0 signature mismatch: expected SIG1 got {sig0}"
        assert sig1 == "SIG2", f"Block 1 signature mismatch: expected SIG2 got {sig1}"
    except AssertionError as e:
        print_stacktrace(e)
        # The bug is present - exit with nonzero code
        sys.exit(1)

    # No assertion error means bug is fixed - exit 0
    print("No leak detected, signatures assigned per block correctly.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```
