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

try:
    # We try to import the RiskGate from the SDK as per the proposal.
    from strands_agents.sdk.vended_interventions.risk_gate import RiskGate
    from strands_agents.sdk.agent import Agent

    # Define dummy tool classes to simulate tools and their names & arguments
    class Tool:
        def __init__(self, name):
            self.name = name

        def __call__(self, *args, **kwargs):
            return {"called": self.name, "args": args, "kwargs": kwargs}

        # For zero config we might need description and schema attributes
        description = ""
        schema = {}

    # Create example tools matching names in the example
    search = Tool("search")
    writeFile = Tool("write_file")
    deleteProdDb = Tool("delete_prod_db")
    charge = Tool("charge")
    sendEmail = Tool("send_email")

    # Instantiate agent with RiskGate, configured as per the proposal
    rg = RiskGate({
        "tools": {
            "search": 'read',
            "write_file": 'write',
            "delete_prod_db": 'destructive',
        },
        "thresholds": {
            "charge": {"field": "amount", "warn": 1000, "deny": 10000},
            "send_email": {"field": "recipients.length", "warn": 5, "deny": 100},
        },
        "read": "proceed",
        "write": "audit",
        "destructive": "escalate",
        "warn": "escalate",
        "deny": "deny",
    })

    agent = Agent(
        tools=[search, writeFile, deleteProdDb, charge, sendEmail],
        interventions=[rg],
    )


    # We will test various calls and assert that RiskGate applies expected decisions according to risk level.

    # The RiskGate interface presumably uses beforeToolCall(tool_name, args)

    # Mimic the call context and verify behavior.
    def test_static_classification():
        # Static classification test:
        for tool, level in [
            (search, 'proceed'),
            (writeFile, 'audit'),
            (deleteProdDb, 'escalate'),
        ]:
            # We expect the intervention to classify, then act accordingly.
            # The SDK's RiskGate behavior must allow us to call beforeToolCall(tool_name, args)
            # and get the intervention's decision
            res = rg.beforeToolCall(tool.name, {})
            # The "read" → "proceed"
            # "write" → "audit"
            # "destructive" → "escalate"
            expected_action = level
            # We'll check that the action name matches expected_action
            # The `beforeToolCall` might return an object with the action or raise on deny
            # We'll check for string attribute 'name' for the action, else just convert to str
            action_name = getattr(res, "name", str(res)).lower()
            assert expected_action in action_name, f"{tool.name} expected {expected_action} got {action_name}"

    def test_thresholds():
        # Test charge tool with amounts below warn, between warn and deny, above deny
        # construct dummy args dict with 'amount'
        tests = [
            ("charge", {"amount": 10}, "proceed"),  # below warn: proceed
            ("charge", {"amount": 5000}, "escalate"),  # between warn(1000) and deny(10000): escalate
            ("charge", {"amount": 20000}, "deny"),  # above deny: deny
        ]
        for tool_name, args, expected_action in tests:
            res = rg.beforeToolCall(tool_name, args)
            action_name = getattr(res, "name", str(res)).lower()
            assert expected_action in action_name, f"{tool_name} with args={args} expected {expected_action} got {action_name}"

        # Test send_email thresholds with recipients length
        tests = [
            ("send_email", {"recipients": ["a@a.com"]}, "proceed"),  # <=5 proceed
            ("send_email", {"recipients": ["a@a.com"]*10}, "escalate"),  # 10>5 warn escalate
            ("send_email", {"recipients": ["a@a.com"]*200}, "deny"),  # 200>100 deny
        ]
        for tool_name, args, expected_action in tests:
            res = rg.beforeToolCall(tool_name, args)
            action_name = getattr(res, "name", str(res)).lower()
            assert expected_action in action_name, f"{tool_name} with args={args} expected {expected_action} got {action_name}"

    def test_audit_mode():
        # Write tools should audit (log + proceed)
        # We just test that write_file maps to audit action
        res = rg.beforeToolCall("write_file", {})
        action_name = getattr(res, "name", str(res)).lower()
        assert "audit" in action_name or "guide" in action_name, f"write_file expected audit got {action_name}"

    # Run tests
    test_static_classification()
    test_thresholds()
    test_audit_mode()

except AssertionError as e:
    print_stacktrace(e)
    sys.exit(1)
except Exception as e:
    print_stacktrace(e)
    sys.exit(1)
else:
    # If no assertions fail, exit 0
    print("RiskGate intervention handler tests passed.")
    sys.exit(0)
```
