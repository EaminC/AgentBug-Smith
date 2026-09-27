import os
import pytest

from crewai.agents.crew_agent_executor import CrewAgentExecutor, AgentAction, AgentFinish
from crewai.tools.structured_tool import StructuredTool
from crewai.task import Task
from crewai.llm import LLM
from crewai.agents.agent_builder.base_agent import BaseAgent


class DummyLLM(LLM):
    def __init__(self):
        super().__init__()
        self.call_count = 0

    def call(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        # Return a dummy response that simulates the agent finishing immediately
        return "Final answer: 42"


class DummyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="dummy_agent")


def multiply_func(args):
    # Simple multiply function for the tool
    return args["a"] * args["b"]


def test_result_as_answer_prevents_llm_calls():
    """
    Test that when a tool has result_as_answer=True, the agent returns the tool output directly
    without making extra LLM calls.
    """

    # Create a structured tool with return_direct=True (alias for result_as_answer)
    multiply_tool = StructuredTool.from_function(
        name="multiply",
        description="Multiply two integers",
        func=multiply_func,
        return_direct=True,
        args_schema=dict  # Use dict for simplicity; real schema not needed here
    )

    # Create a dummy LLM that counts calls
    dummy_llm = DummyLLM()

    # Create a dummy agent
    dummy_agent = DummyAgent()

    # Prepare the prompt and tools list
    prompt = {"input": "Multiply 6 and 7"}
    tools = [multiply_tool]

    # Create the CrewAgentExecutor with the dummy LLM and the multiply tool
    executor = CrewAgentExecutor(
        agent=dummy_agent,
        prompt=prompt,
        max_iter=5,
        tools=tools,
        tools_names="multiply",
        stop_words=[],
        tools_description="Multiply tool",
        llm=dummy_llm,
        verbose=False,
        step_callback=None,
        training_handler=None,
        crew=None,
        max_rpm=1000,
        max_tokens=1000,
        max_iterations=5,
        max_tokens_per_iteration=1000,
        max_tokens_per_prompt=1000,
        max_tokens_completion=1000,
    )

    # Manually create an AgentAction that calls the multiply tool with arguments
    agent_action = AgentAction(tool="multiply", tool_input={"a": 6, "b": 7}, text="")

    # Use the internal method to simulate the tool execution and check finality
    tool_result = executor._execute_tool_and_check_finality(agent_action)

    # Assert the tool result is correct
    assert tool_result.result == 42

    # Assert that result_as_answer is True for this tool
    assert tool_result.result_as_answer is True

    # Now simulate the agent processing the action and returning the final answer immediately
    finish = executor._invoke_loop(formatted_answer=agent_action)

    # The returned object should be an AgentFinish instance
    assert isinstance(finish, AgentFinish)

    # The output of the AgentFinish should be the tool result (42)
    assert finish.output == 42

    # The LLM call count should be zero or one (depending on implementation),
    # but importantly it should NOT be more than one (no extra calls after tool result)
    # Because the bug was that LLM calls happened even when result_as_answer=True.
    # We expect zero or one call only.
    assert dummy_llm.call_count <= 1