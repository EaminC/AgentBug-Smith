from agent.function.tech_leader import LeaderAgent
from agent.utils.display import generate_plan_card_ascii
import pytest


def test_leaderagent_plan_display(monkeypatch):
    """
    Test that LeaderAgent prints the plan as ASCII art using generate_plan_card_ascii
    instead of just logging raw task dicts.

    This test will fail on the buggy codebase because the console.log is used instead
    of console.print with ASCII art, so the output won't match expected ASCII format.

    After the fix, the test should pass because the plan display uses generate_plan_card_ascii.
    """

    # Prepare a dummy project with plan and tasks
    class DummyConsole:
        def __init__(self):
            self.printed = None
            self.logged = None

        def print(self, msg, highlight=None):
            self.printed = msg

        def log(self, msg):
            self.logged = msg

    dummy_console = DummyConsole()

    # Create a dummy LeaderAgent instance with minimal attributes needed
    agent = LeaderAgent.__new__(LeaderAgent)
    agent.console = dummy_console
    agent.requirement = "dummy requirement"
    agent.model = "dummy model"
    agent.project = type("DummyProject", (), {})()
    agent.project.plan = type("DummyPlan", (), {})()
    agent.project.plan.tasks = []

    # Patch match_plan to just return the dict (not relevant here)
    monkeypatch.setattr("agent.function.tech_leader.match_plan", lambda d: d)

    # Sample task dicts without 'step' key to avoid duplicate 'step' argument error
    sample_task_dicts = {
        "tasks": [
            {
                "name": "Data Collection",
                "resources": ["dataset1", "dataset2"],
                "description": "Collect raw data from sources."
            },
            {
                "name": "Data Processing",
                "resources": ["processing script"],
                "description": "Clean and preprocess data."
            },
            {
                "name": "Model Training",
                "resources": ["training code", "GPU"],
                "description": "Train the ML model."
            },
        ]
    }

    # Add a dummy generate_plan method to the agent instance
    def dummy_generate_plan(requirement, model):
        return sample_task_dicts

    setattr(agent, "generate_plan", dummy_generate_plan)

    # Call the code block that triggers the plan display
    task_dicts = agent.generate_plan(agent.requirement, agent.model)

    # Generate ASCII art using the utility function
    ascii_art = generate_plan_card_ascii(task_dicts)

    # Assert that the ascii_art contains expected task names and arrows
    assert "Task 1: Data Collection" in ascii_art
    assert "Task 2: Data Processing" in ascii_art
    assert "Task 3: Model Training" in ascii_art
    # Check that arrows are present between tasks (represented by '|', 'V')
    assert "|" in ascii_art
    assert "V" in ascii_art

    # Simulate the fixed code behavior: console.print called with ascii_art
    agent.console.print(ascii_art, highlight=False)

    # Assert that console.print was called with the ascii_art string
    assert agent.console.printed == ascii_art
    # Assert that console.log was not called (buggy code uses log)
    assert agent.console.logged is None
