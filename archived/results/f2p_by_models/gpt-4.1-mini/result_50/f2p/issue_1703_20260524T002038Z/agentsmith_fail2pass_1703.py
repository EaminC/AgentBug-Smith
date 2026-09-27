from unittest.mock import patch

import pytest

from crewai.agent import Agent
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.task import Task
from crewai.utilities.planning_handler import CrewPlanner


@patch('crewai.knowledge.storage.knowledge_storage.chromadb')
def test_agent_knowledge_included_in_planning_summary(mock_chroma):
    """
    Test that verifies agent knowledge is included in the crew planning task summary.
    This test should fail on the buggy codebase where knowledge is omitted,
    and pass after the fix where knowledge is included.
    """
    # Setup mock for chromadb to avoid external calls
    mock_collection = mock_chroma.return_value.get_or_create_collection.return_value
    mock_collection.add.return_value = None

    # Create an agent with knowledge source
    knowledge_content = "Critical knowledge about AI systems."
    knowledge_source = StringKnowledgeSource(content=knowledge_content)
    agent = Agent(
        role="Knowledgeable Agent",
        goal="Use knowledge to plan tasks",
        backstory="Experienced agent with domain knowledge",
        knowledge_sources=[knowledge_source]
    )

    # Create a task assigned to the agent
    task = Task(
        description="Analyze AI system requirements",
        expected_output="Detailed analysis report",
        agent=agent
    )

    # Create a CrewPlanner with this single task
    planner = CrewPlanner(tasks=[task], planning_agent_llm=None)

    # Generate the tasks summary string
    tasks_summary = planner._create_tasks_summary()

    # Assertions to verify knowledge inclusion
    assert knowledge_content in tasks_summary, (
        "Knowledge content should be included in the tasks summary for planning."
    )
    assert '"agent_knowledge"' in tasks_summary, (
        "The tasks summary should include the 'agent_knowledge' field when knowledge is present."
    )
    assert task.description in tasks_summary, (
        "Task description should be present in the tasks summary."
    )
    assert agent.role in tasks_summary, (
        "Agent role should be present in the tasks summary."
    )
    assert task.expected_output in tasks_summary, (
        "Task expected output should be present in the tasks summary."
    )
