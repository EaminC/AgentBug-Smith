```python
# reproducer.py
import sys
import traceback

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
    try:
        from strands import Agent
        from strands.models import BedrockModel

        # You must fill in your guardrail id here where indicated
        GUARDRAIL_ID = "<your-guardrail-id>"
        GUARDRAIL_VERSION = "1"

        # Minimal dummy tool that simulates domain text returned by a knowledge base
        class DummyKBTool:
            name = "kb_tool"
            def __call__(self, query: str):
                # Simulate a tool returning knowledge base passages as tool result
                return {
                    "role": "user",
                    "content": [{"text": {"text": "Simulated knowledge base passage about taxes."}}],
                    "type": "toolResult",
                }

        # Create a BedrockModel with guardrail_latest_message=True and the dummy tool
        model = BedrockModel(
            model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            region_name="us-east-1",
            guardrail_id=GUARDRAIL_ID,
            guardrail_version=GUARDRAIL_VERSION,
            guardrail_latest_message=True,
        )

        agent = Agent(model=model, tools=[DummyKBTool()])

        # Call the agent once to kick off conversation
        # The issue only appears after a tool execution cycle
        # We invoke the agent with an input that triggers the tool
        question = "what is the standard deduction?"

        # The agent call returns a dict with possible keys including "guardrail_intervened"
        output = agent(question)

        # Check if output signals guardrail intervention false positive
        # According to the description, this happens because guardContent wrapping is lost
        if output.get("guardrail_intervened", False):
            # If guardrail_intervened is True, we still can't be sure it's a false positive,
            # but based on the description, this indicates the failure mode.
            raise AssertionError("Bug triggered: False positive guardrail intervention after tool execution")

        # If no false positive, exit 0 normally
    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
```