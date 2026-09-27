from unittest.mock import patch

import pytest

from crewai.agent import Agent
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.task import Task
from crewai.utilities.planning_handler import CrewPlanner


@patch('crewai.knowledge.storage.knowledge_storage.chromadb')
def test_knowledge_included_in_planning_summary(mock_chroma):
    """Test that agent knowledge sources are included in the planning task summary.
    
    This is a regression test for issue #1703 - Knowledge not included in the 
    agent planning process.
    """
    # Mock ChromaDB to avoid needing a real database
    mock_collection = mock_chroma.return_value.get_or_create_collection.return_value
    mock_collection.add.return_value = None
    
    # Create a knowledge source with distinctive content
    knowledge_content = "Critical planning context: AI systems require validation steps"
    knowledge_source = StringKnowledgeSource(content=knowledge_content)
    
    # Create an agent with the knowledge source
    agent = Agent(
        role="AI Researcher",
        goal="Research AI systems",
        backstory="Expert in AI with deep knowledge",
        knowledge_sources=[knowledge_source]
    )
    
    # Create a task for this agent
    task = Task(
        description="Analyze AI validation requirements",
        expected_output="Analysis report",
        agent=agent
    )
    
    # Create the crew planner
    planner = CrewPlanner([task], None)
    
    # Generate the tasks summary used for planning
    tasks_summary = planner._create_tasks_summary()
    
    # Verify that knowledge is included in the planning summary
    assert '"agent_knowledge"' in tasks_summary, \
        "agent_knowledge field should be present in task summary when knowledge exists"
    assert knowledge_content in tasks_summary, \
        "Knowledge content should be present in task summary"
