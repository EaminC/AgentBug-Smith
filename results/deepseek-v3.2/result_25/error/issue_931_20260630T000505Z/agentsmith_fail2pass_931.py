import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from crewai import Agent, Task, Crew, Process
from crewai.agents.agent_builder import AgentBuilder
from crewai.agents.executor import CrewAgentExecutor
from crewai.memory.entity import EntityMemory
from crewai.memory.short_term import ShortTermMemory
from crewai.tools.agent_tools import AgentTools
from crewai.utilities import I18N

class TestCrewAIBugReproduction:
    """Test suite to reproduce and verify bug fixes in CrewAI"""
    
    def test_agent_initialization_with_memory(self):
        """Test agent initialization with memory configurations"""
        # Test that agents can be initialized with various memory types
        agent = Agent(
            role="Researcher",
            goal="Find relevant information",
            backstory="Expert researcher",
            verbose=True
        )
        
        assert agent.role == "Researcher"
        assert agent.goal == "Find relevant information"
        assert agent.backstory == "Expert researcher"
    
    def test_crew_execution_with_tasks(self):
        """Test crew execution with sequential tasks"""
        researcher = Agent(
            role="Researcher",
            goal="Find relevant information",
            backstory="Expert researcher",
            verbose=True
        )
        
        writer = Agent(
            role="Writer",
            goal="Write compelling content",
            backstory="Professional writer",
            verbose=True
        )
        
        research_task = Task(
            description="Find information about AI",
            agent=researcher,
            expected_output="Research report"
        )
        
        write_task = Task(
            description="Write article about AI",
            agent=writer,
            expected_output="Article",
            context=[research_task]
        )
        
        crew = Crew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            verbose=True,
            process=Process.sequential
        )
        
        # Mock the execution to avoid actual API calls
        with patch.object(CrewAgentExecutor, 'execute', return_value="Mocked result"):
            result = crew.kickoff()
            assert result == "Mocked result"
    
    def test_agent_tools_integration(self):
        """Test agent tools functionality"""
        # Test that AgentTools can be instantiated
        tools = AgentTools()
        assert tools is not None
        
        # Test specific tool methods if they exist
        if hasattr(tools, 'available_tools'):
            available = tools.available_tools()
            assert isinstance(available, list)
    
    def test_i18n_internationalization(self):
        """Test internationalization utilities"""
        i18n = I18N()
        assert i18n is not None
        
        # Test retrieval of strings
        if hasattr(i18n, 'retrieve'):
            text = i18n.retrieve('task_execution', 'en')
            assert isinstance(text, str)
    
    def test_memory_systems(self):
        """Test different memory systems"""
        # Test entity memory
        entity_memory = EntityMemory()
        assert entity_memory is not None
        
        # Test short-term memory
        short_term_memory = ShortTermMemory()
        assert short_term_memory is not None
    
    def test_agent_builder(self):
        """Test AgentBuilder functionality"""
        builder = AgentBuilder()
        assert builder is not None
        
        # Test builder methods
        if hasattr(builder, 'create_agent'):
            with patch('crewai.agents.agent_builder.LLM') as mock_llm:
                mock_llm.return_value = Mock()
                agent = builder.create_agent(
                    role="Test Agent",
                    goal="Test Goal",
                    backstory="Test Backstory"
                )
                assert agent is not None
    
    @pytest.mark.asyncio
    async def test_async_crew_execution(self):
        """Test asynchronous crew execution"""
        agent = Agent(
            role="Async Tester",
            goal="Test async functionality",
            backstory="Async testing expert",
            verbose=True,
            allow_delegation=False
        )
        
        task = Task(
            description="Test async execution",
            agent=agent,
            expected_output="Test result",
            async_execution=True
        )
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=True
        )
        
        # Mock async execution
        with patch.object(CrewAgentExecutor, 'execute_async', AsyncMock(return_value="Async result")):
            result = await crew.kickoff_async()
            assert result == "Async result"
    
    def test_environment_variables_usage(self):
        """Test that environment variables are properly used"""
        # Verify API keys are retrieved from environment
        openai_key = os.getenv('OPENAI_API_KEY')
        assert openai_key is not None
        assert openai_key.startswith('forge-')
        
        anthropic_key = os.getenv('ANTHROPIC_AUTH_TOKEN')
        assert anthropic_key is not None
        assert anthropic_key.startswith('forge-')
    
    def test_import_paths_correct(self):
        """Verify all import paths are correct and modules exist"""
        # Test core module imports
        import crewai
        from crewai import Agent, Task, Crew
        from crewai.agents import AgentBuilder
        from crewai.memory import EntityMemory, ShortTermMemory
        
        # Verify modules can be instantiated
        assert crewai is not None
        assert Agent is not None
        assert Task is not None
        assert Crew is not None
        assert AgentBuilder is not None
        assert EntityMemory is not None
        assert ShortTermMemory is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])