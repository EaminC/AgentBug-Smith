```python
# reproducer.py
import sys
import asyncio

from functools import wraps

# Simulated minimal crewai classes and decorators to reproduce the issue

class Agent:
    def __init__(self, config=None, tools=None):
        self.config = config
        self.tools = tools
        self.name = "AgentName"

class Task:
    def __init__(self, config=None):
        self.config = config
        self.name = "TaskName"

class Crew:
    def __init__(self, agents=None, tasks=None, process=None):
        self.agents = agents or []
        self.tasks = tasks or []
        self.process = process
        self.name = "CrewName"
    async def kickoff_async(self, inputs):
        # Simulate kickoff by just returning a fixed string
        return "kickoff done"


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

# Original decorators WITHOUT async support (the source of the problem)
def agent(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Does not await async functions - returns coroutine object when func is async
        return func(self, *args, **kwargs)
    return wrapper

def task(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Similar issue
        return func(self, *args, **kwargs)
    return wrapper

def crew(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Similar issue
        return func(self, *args, **kwargs)
    return wrapper


class FounderCrew:
    agents_config = {"your-agent": {"some": "config"}}
    tasks_config = {"your-agent": {"some": "config"}}

    async def _create_tools(self):
        # Simulate async tool creation
        await asyncio.sleep(0.01)
        return ["tool1", "tool2"]

    @agent
    async def your_agent(self) -> Agent:
        # Async method decorated by @agent which does NOT await the coroutine inside
        tools = await self._create_tools()
        return Agent(config=self.agents_config["your-agent"], tools=tools)

    @task
    async def your_task(self) -> Task:
        return Task(config=self.tasks_config["your-agent"])

    @crew
    async def crew(self, run_mode: str = "answer") -> Crew:
        # Await async decorated methods, which themselves return coroutines (unawaited)
        # Because your_agent() returns coroutine (due to decorator), awaiting it is mandatory.
        # But the decorator does not await so returns a coroutine object => this likely fails downstream.
        # We'll keep this call, it might error out because your_agent returns coroutine.
        agents = [await self.your_agent()]
        tasks = [await self.your_task()]
        return Crew(agents=agents, tasks=tasks, process="sequential")

async def reproduce_issue():
    crew_instance = FounderCrew()
    try:
        # The critical line - calling crew and kickoff_async (async kickoff)
        cr = await crew_instance.crew()
        # cr should be a Crew instance if decorators worked fine.
        # But if decorators return coroutine object instead of awaited Agent or Task,
        # cr would be invalid and cause attribute errors on next usage.
        # So let's assert that cr has attribute "name" (Crew must have a name attribute)
        assert hasattr(cr, "name") and isinstance(cr.name, str), "Returned crew object missing .name"
        # Call kickoff_async to simulate production usage
        result = await cr.kickoff_async(inputs={})
        assert result == "kickoff done"
    except Exception as e:
        print_stacktrace(e)
        # Because the bug causes coroutine object to be returned where it shouldn't,
        # we expect AttributeError or similar, so raise AssertionError to mark reproducing bug.
        raise AssertionError("Issue reproduced - decorators do not support awaiting async methods") from e

def main():
    # Run async reproduction and catch assertion
    try:
        asyncio.run(reproduce_issue())
    except AssertionError as e:
        # Bug present, exit with error code 1
        print(f"\n{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        # Unexpected error
        print(f"\nUnexpected error: {exc}", file=sys.stderr)
        sys.exit(2)
    else:
        print("No issue detected: decorators support async methods as expected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
```
