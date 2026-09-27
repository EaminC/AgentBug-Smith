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

def main():
    # We simulate the crewAI framework's behavior with minimal dummy classes and infrastructure.
    # The user's code snippet uses decorators `@router` and `@listen`, and calls some external
    # crew kickoff with outputs.

    # We create a simulation environment that reproduces the sequential execution of the example,
    # especially to verify if multiple routers triggered by the same upstream event react and dispatch
    # their own downstream events, or only the last router does. We will raise AssertionError if
    # only some routers trigger and not all expected ones.

    # Simulated minimal framework of router and listen:
    events_triggered = []  # collects all events emitted by router methods
    events_listened = []   # collects all events handled by listen methods

    # Decorators will register functions by name
    routers = {}
    listens = {}

    def router(trigger):
        # trigger is a function or string that routes call this one
        # In this stripped environment, it will just decorate and register
        def decorator(fn):
            name = fn.__name__
            if trigger not in routers:
                routers[trigger] = []
            routers[trigger].append(fn)
            return fn
        return decorator

    def listen(event_name):
        def decorator(fn):
            listens[event_name] = fn
            return fn
        return decorator

    # Simplified "state" holder
    class State:
        def __init__(self):
            self.patient_data = "dummy data"
            self.total_token_usage = 0
            self.scan_medical = ""
            self.diagnosed_conditions = ""

    # Simulated MedicalScannerCrew and MedicalDiagnosisCrew return a dummy "result" with .raw and .token_usage.total_tokens
    class DummyTokenUsage:
        def __init__(self, total_tokens):
            self.total_tokens = total_tokens

    class DummyResult:
        def __init__(self, raw, total_tokens=1):
            self.raw = raw
            self.token_usage = DummyTokenUsage(total_tokens)

    class MedicalScannerCrew:
        def crew(self):
            return self
        def kickoff(self, inputs):
            # returns scan that contains characters "DHA"
            return DummyResult(raw="DHA", total_tokens=5)

    class MedicalDiagnosisCrew:
        def crew(self):
            return self
        def kickoff(self, inputs):
            # Expects inputs["data"] and will just return it as raw
            return DummyResult(raw=inputs["data"], total_tokens=3)

    # Now we translate the user's code into this environment:

    class ScanFlow:
        def __init__(self):
            self.state = State()

        def start(self):
            self.scan_medical()
            self.diagnose_conditions()

        def scan_medical(self):
            # user code
            print("Scanning medical data")
            result = MedicalScannerCrew().crew().kickoff(inputs={"data": str(self.state.patient_data)})
            print("Scan result: ", result.raw)
            self.state.total_token_usage += result.token_usage.total_tokens
            print("Medical data obtained", result.raw)
            self.state.scan_medical = result.raw
            print("Saving medical scan data")

        @router(scan_medical)
        def diagnose_conditions(self):
            print("Diagnosing medical conditions")
            result = MedicalDiagnosisCrew().crew().kickoff(inputs={"data": self.state.scan_medical})
            self.state.diagnosed_conditions = result.raw
            print("Diagnosed conditions: ", self.state.diagnosed_conditions)
            # After diagnosis, fire the routers observing diagnose_conditions
            for fn in routers.get(self.diagnose_conditions, []):
                route = fn(self)
                if route is not None:
                    # they return event names, record and trigger listen
                    events_triggered.append(route)
                    if route in listens:
                        listens[route](self)
                        events_listened.append(route)

        @router(diagnose_conditions)
        def diabetes_router(self):
            print("Diabetes Router")
            if "D" in self.state.diagnosed_conditions:
                print("Diabetes detected")
                return "diabetes"

        @listen("diabetes")
        def diabetes_analysis(self):
            print("Performing detailed diabetes analysis")

        @router(diagnose_conditions)
        def hypertension_router(self):
            print("Hypertension Router")
            if "H" in self.state.diagnosed_conditions:
                print("Hypertension detected")
                return "hypertension"

        @listen("hypertension")
        def hypertension_analysis(self):
            print("Performing detailed hypertension analysis")

        @router(diagnose_conditions)
        def anemia_router(self):
            print("Anemia Router")
            if "A" in self.state.diagnosed_conditions:
                print("Anemia detected")
                return "anemia"

        @listen("anemia")
        def anemia_analysis(self):
            print("Performing detailed anemia analysis")

    # We must patch ScanFlow to use these decorators defined here:
    # They have registered routers and listens themselves but ScanFlow defines them again,
    # so to link those decorators to ScanFlow methods, let's overwrite the original ScanFlow
    # with decorated methods from instance methods:

    scanflow = ScanFlow()

    # Patch the router functions to ScanFlow class manually with our decorators:
    # Our router decorator collects functions by the trigger function, so we have a single
    # dict routers mapping function triggers to a list of router methods.
    # But note that ScanFlow.diagnose_conditions method calls routers.get to find all routers.

    # But these methods are instance methods, not functions, so adjusting to method object:
    # We must register the correct instance methods.

    # Clear routers and listens, then register with correct bound methods
    routers.clear()
    listens.clear()

    # Helpers to register router methods for diagnose_conditions trigger:
    def reg_router(fn):
        if scanflow.diagnose_conditions not in routers:
            routers[scanflow.diagnose_conditions] = []
        routers[scanflow.diagnose_conditions].append(fn)

    def reg_listen(event_name, fn):
        listens[event_name] = fn

    reg_router(scanflow.diabetes_router)
    reg_router(scanflow.hypertension_router)
    reg_router(scanflow.anemia_router)

    reg_listen("diabetes", scanflow.diabetes_analysis)
    reg_listen("hypertension", scanflow.hypertension_analysis)
    reg_listen("anemia", scanflow.anemia_analysis)

    # Now run start flow:
    scanflow.start()

    # We expect events_triggered to include "diabetes", "hypertension", "anemia"
    # from diagnose_conditions routers.

    try:
        assert "diabetes" in events_triggered, "Diabetes router did not trigger event"
        assert "hypertension" in events_triggered, "Hypertension router did not trigger event"
        assert "anemia" in events_triggered, "Anemia router did not trigger event"

        # Check listeners triggered too:
        assert "diabetes" in events_listened, "Diabetes listener did not trigger"
        assert "hypertension" in events_listened, "Hypertension listener did not trigger"
        assert "anemia" in events_listened, "Anemia listener did not trigger"

    except AssertionError as e:
        print_stacktrace(e)
        raise e

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.exit(1)
    sys.exit(0)
```
