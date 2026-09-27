import os
import pytest
from crewai import Agent, Task, Crew, Process, LLM
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource


def test_agent_with_knowledge_source_no_api_status_error():
    # Create a knowledge source
    content = "Users name is John. He is 30 years old and lives in San Francisco."
    string_source = StringKnowledgeSource(
        content=content,
    )

    # Create an LLM with a temperature of 0 to ensure deterministic outputs
    # Use environment variable for model and API key to avoid authentication errors
    llm = LLM(model=os.getenv("MODEL", "gpt-4o-mini"), temperature=0)

    # Create an agent with the knowledge store
    agent = Agent(
        role="About User",
        goal="You know everything about the user.",
        backstory="""You are a master at understanding people and their preferences.""",
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )
    task = Task(
        description="Answer the following questions about the user: {question}",
        expected_output="An answer to the question.",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
        process=Process.sequential,
        knowledge_sources=[string_source],  # Enable knowledge by adding the sources here.
    )

    result = crew.kickoff(inputs={"question": "What city does John live in and how old is he?"})

    # The result should be a dictionary containing the task output without raising APIStatusError
    assert isinstance(result, dict)
    assert task.description.split(":")[0] in result or "answer" in str(result).lower()
    # Check that the answer contains expected information
    answer_str = str(result).lower()
    assert "san francisco" in answer_str
    assert "30" in answer_str or "thirty" in answer_str