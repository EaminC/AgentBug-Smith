from crewai.agent import Agent
from crewai.crew import Crew
from crewai.task import Task
from crewai.tasks.task_output import TaskOutput
from crewai.process import Process
from unittest.mock import patch, ANY
import pytest


def test_context_passed_when_explicitly_empty_context():
    """
    Test that when a task is created with context=[] (explicit empty list),
    the task does NOT receive context from previous tasks.

    This test reproduces the bug described in issue #2789:
    Before fix: context from previous tasks is passed even if context=[]
    After fix: context is empty string as expected.
    """
    # Create agents
    agent1 = Agent(
        role="Agent 1",
        goal="Goal 1",
        backstory="Backstory 1",
        allow_delegation=False,
    )
    agent2 = Agent(
        role="Agent 2",
        goal="Goal 2",
        backstory="Backstory 2",
        allow_delegation=False,
    )
    agent3 = Agent(
        role="Agent 3",
        goal="Goal 3",
        backstory="Backstory 3",
        allow_delegation=False,
    )

    # Create three tasks, third task has context=[]
    task1 = Task(
        description="Task 1 description",
        expected_output="Output 1",
        agent=agent1,
    )
    task2 = Task(
        description="Task 2 description",
        expected_output="Output 2",
        agent=agent2,
        context=[task1],
    )
    task3 = Task(
        description="Task 3 description",
        expected_output="Output 3",
        agent=agent3,
        context=[],
    )

    # Create crew with sequential process
    crew = Crew(
        agents=[agent1, agent2, agent3],
        tasks=[task1, task2, task3],
        process=Process.sequential,
    )

    # Patch Task.execute_sync to capture the context argument passed to task3
    with patch.object(Task, "execute_sync") as mock_execute_sync:
        # Setup return values for execute_sync for all tasks
        mock_execute_sync.side_effect = [
            TaskOutput(description="Task 1 output", raw="Output from task 1", agent=agent1.role),
            TaskOutput(description="Task 2 output", raw="Output from task 2", agent=agent2.role),
            TaskOutput(description="Task 3 output", raw="Output from task 3", agent=agent3.role),
        ]

        crew.kickoff()

        # The last call corresponds to task3 execution
        # Extract the context argument passed to execute_sync for task3
        # execute_sync called with signature: execute_sync(self, context=None, tools=None, agent=None)
        # So context is a keyword argument
        last_call = mock_execute_sync.call_args_list[-1]
        kwargs = last_call.kwargs
        passed_context = kwargs.get("context", None)

        # Assert that the context passed to task3 is an empty string (no context)
        # Before fix, it would be a string containing outputs from previous tasks
        assert passed_context == "", (
            "Expected empty context string for task with context=[], "
            "but got non-empty context."
        )
