import pytest
from unittest.mock import patch

from crewai.agent import Agent
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.task import Task
from crewai.utilities.planning_handler import CrewPlanner


@pytest.mark.parametrize(
    "knowledge_content",
    [
        "Critical knowledge for planning",
        "AI systems require careful training and validation.",
    ],
)
@patch("crewai.knowledge.storage.knowledge_storage.chromadb")
def test_agent_knowledge_included_in_planning_summary(mock_chroma, knowledge_content):
    """
    This test verifies that when an Agent has knowledge sources,
    the knowledge content is included in the task summary generated
    by the CrewPlanner. Before the fix, knowledge was omitted from
    the planning prompt, so this test should fail on the buggy codebase
    and pass after the fix.
    """
    # Mock ChromaDB collection to avoid real network calls
    mock_collection = mock_chroma.return_value.get_or_create_collection.return_value
    mock_collection.add.return_value = None

    # Create an agent with a knowledge source containing the test content
    agent = Agent(
        role="Planner Agent",
        goal="Plan tasks effectively",
        backstory="Experienced planner",
        knowledge_sources=[StringKnowledgeSource(content=knowledge_content)],
    )

    # Create a task assigned to the agent
    task = Task(
        description="Plan the execution of tasks",
        expected_output="Detailed plan including knowledge",
        agent=agent,
    )

    # Create a CrewPlanner with this single task
    planner = CrewPlanner(tasks=[task], planning_agent_llm=None)

    # Generate the tasks summary string which should include knowledge
    tasks_summary = planner._create_tasks_summary()

    # Assert that the knowledge content is included in the summary string
    assert knowledge_content in tasks_summary, (
        "Knowledge content should be included in the tasks summary for planning."
    )

    # Also assert that the agent_knowledge field is present in the summary
    assert '"agent_knowledge"' in tasks_summary, (
        "The 'agent_knowledge' field should be present in the tasks summary."
    )

    # Assert other expected fields are present
    assert task.description in tasks_summary
    assert task.expected_output in tasks_summary
    assert agent.role in tasks_summary
