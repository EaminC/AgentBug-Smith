import json
from unittest.mock import patch

import pytest

from crewai.agent import Agent
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.task import Task
from crewai.tools.base_tool import BaseTool
from crewai.utilities.planning_handler import CrewPlanner


class TestKnowledgePlanning:
    """
    Tests for verifying the integration of knowledge sources in the planning process.
    These tests are designed to fail on buggy code (knowledge not included) and pass after fix.
    """

    @patch('crewai.knowledge.storage.knowledge_storage.chromadb')
    def test_knowledge_inclusion_with_mocked_chroma(self, mock_chroma):
        """
        Test that knowledge IS included when agent has knowledge sources.
        This test should FAIL on buggy code, PASS after fix.
        """
        # Mock ChromaDB to avoid embedding errors
        mock_collection = mock_chroma.return_value.get_or_create_collection.return_value
        mock_collection.add.return_value = None

        # Create agent WITH knowledge
        agent = Agent(
            role="Scientist",
            goal="Study",
            backstory="Background",
            knowledge_sources=[
                StringKnowledgeSource(content="Important scientific fact.")
            ]
        )

        task = Task(
            description="Study topic",
            expected_output="Report",
            agent=agent
        )

        planner = CrewPlanner([task], None)
        task_summary = planner._create_tasks_summary()

        # Before fix: these will fail
        # After fix: these will pass
        assert "Important scientific fact." in task_summary
        assert '"agent_knowledge"' in task_summary

    @patch('crewai.knowledge.storage.knowledge_storage.chromadb')
    def test_no_knowledge_no_field(self, mock_chroma):
        """
        Test that agent_knowledge field is NOT present when agent has no knowledge.
        This test should PASS on both buggy and fixed code.
        """
        mock_collection = mock_chroma.return_value.get_or_create_collection.return_value
        mock_collection.add.return_value = None

        agent = Agent(
            role="Analyst",
            goal="Analyze",
            backstory="No knowledge"
        )

        task = Task(
            description="Analyze data",
            expected_output="Analysis",
            agent=agent
        )

        planner = CrewPlanner([task], None)
        task_summary = planner._create_tasks_summary()

        # Should always pass: no knowledge -> no field
        assert '"agent_knowledge"' not in task_summary

    @patch('crewai.knowledge.storage.knowledge_storage.chromadb')
    def test_multiple_knowledge_sources(self, mock_chroma):
        """
        Test with multiple knowledge sources (only first should be included per patch).
        This test should FAIL on buggy code, PASS after fix.
        """
        mock_collection = mock_chroma.return_value.get_or_create_collection.return_value
        mock_collection.add.return_value = None

        agent = Agent(
            role="Historian",
            goal="Document history",
            backstory="Expert",
            knowledge_sources=[
                StringKnowledgeSource(content="First fact."),
                StringKnowledgeSource(content="Second fact.")
            ]
        )

        task = Task(
            description="Document events",
            expected_output="Timeline",
            agent=agent
        )

        planner = CrewPlanner([task], None)
        task_summary = planner._create_tasks_summary()

        # Before fix: fails
        # After fix: passes (only first knowledge source is included per the patch)
        assert '"agent_knowledge"' in task_summary
        assert '\\"First fact.\\"' in task_summary
        assert '\\"Second fact.\\"' not in task_summary  # Only first is included

    @patch('crewai.knowledge.storage.knowledge_storage.chromadb')
    def test_knowledge_with_tools(self, mock_chroma):
        """
        Test knowledge inclusion when tools are also present.
        This test should FAIL on buggy code, PASS after fix.
        """
        mock_collection = mock_chroma.return_value.get_or_create_collection.return_value
        mock_collection.add.return_value = None

        # Create a proper mock tool that satisfies BaseTool requirements
        class MockTool(BaseTool):
            name: str = "mock_tool"
            description: str = "A mock tool for testing"

            def __init__(self):
                super().__init__(name="mock_tool", description="A mock tool for testing")

            def _run(self, *args, **kwargs):
                return "mock result"

            def _generate_description(self):
                return self.description

        agent = Agent(
            role="Engineer",
            goal="Build",
            backstory="Constructor",
            tools=[MockTool()],
            knowledge_sources=[
                StringKnowledgeSource(content="Engineering principle.")
            ]
        )

        task = Task(
            description="Build something",
            expected_output="Built object",
            agent=agent
        )

        planner = CrewPlanner([task], None)
        task_summary = planner._create_tasks_summary()

        # Before fix: fails (knowledge not included)
        # After fix: passes
        assert '"agent_knowledge"' in task_summary
        assert '\\"Engineering principle.\\"' in task_summary
        # Tools should also be present
        assert '"agent_tools": [' in task_summary

    def test_knowledge_formatting(self):
        """
        Test that knowledge is formatted as a JSON‑like string in the summary.
        This test should FAIL on buggy code, PASS after fix.
        """
        # We need to mock chromadb for StringKnowledgeSource initialization
        with patch('crewai.knowledge.storage.knowledge_storage.chromadb'):
            agent = Agent(
                role="Researcher",
                goal="Research",
                backstory="Academic",
                knowledge_sources=[
                    StringKnowledgeSource(content="Test content with \"quotes\".")
                ]
            )

            task = Task(
                description="Research topic",
                expected_output="Findings",
                agent=agent
            )

            planner = CrewPlanner([task], None)
            task_summary = planner._create_tasks_summary()

            # Before fix: fails
            # After fix: passes
            assert '"agent_knowledge"' in task_summary
            # The patch shows format: "[\\"Test content with \"quotes\".\\"]"
            # So we check for escaped quotes
            assert '\\"' in task_summary
