import pytest

from strands import Agent
from strands.tools import tool
from strands.vended_interventions.hitl import HumanInTheLoop
from strands.vended_interventions.hitl.classifier import ClassifierResult
from tests.fixtures.mocked_model_provider import MockedModelProvider


def tool_use_message(name: str, tool_use_id: str = "tool-1", tool_input: dict | None = None) -> dict:
    return {
        "role": "assistant",
        "content": [{"toolUse": {"toolUseId": tool_use_id, "name": name, "input": tool_input or {}}}],
    }


def text_message(text: str) -> dict:
    return {"role": "assistant", "content": [{"text": text}]}


class TestClassifierMode:
    """Tests for the classifier option that enables LLM-driven risk classification."""

    def test_classifier_true_interrupts_when_risky(self):
        from unittest.mock import MagicMock

        executed = []

        @tool(name="delete_file")
        def delete_file() -> str:
            executed.append(True)
            return "deleted"

        agent_model = MockedModelProvider(
            [tool_use_message("delete_file", tool_input={"path": "/data"}), text_message("Done")]
        )

        mock_classifier = MagicMock(
            return_value=ClassifierResult(requires_human_in_the_loop=True, reason="destructive operation")
        )

        agent = Agent(
            model=agent_model,
            tools=[delete_file],
            interventions=[HumanInTheLoop(classifier=mock_classifier)],
        )

        result = agent("Delete the file")

        assert result.stop_reason == "interrupt"
        assert executed == []
        assert "destructive operation" in result.interrupts[0].reason

    def test_classifier_allows_tool_when_not_risky(self):
        from unittest.mock import MagicMock

        executed = []

        @tool(name="read_file")
        def read_file() -> str:
            executed.append(True)
            return "content"

        agent_model = MockedModelProvider(
            [tool_use_message("read_file", tool_input={"path": "/tmp/x"}), text_message("Done")]
        )

        mock_classifier = MagicMock(
            return_value=ClassifierResult(requires_human_in_the_loop=False, reason="read-only operation")
        )

        agent = Agent(
            model=agent_model,
            tools=[read_file],
            interventions=[HumanInTheLoop(classifier=mock_classifier)],
        )

        result = agent("Read the file")

        assert result.stop_reason == "end_turn"
        assert executed == [True]

    def test_allowed_tools_bypasses_classifier(self):
        from unittest.mock import MagicMock

        executed = []

        @tool(name="read_file")
        def read_file() -> str:
            executed.append(True)
            return "content"

        agent_model = MockedModelProvider([tool_use_message("read_file"), text_message("Done")])

        mock_classifier = MagicMock(
            return_value=ClassifierResult(requires_human_in_the_loop=True, reason="should not be called")
        )

        agent = Agent(
            model=agent_model,
            tools=[read_file],
            interventions=[HumanInTheLoop(allowed_tools=["read_file"], classifier=mock_classifier)],
        )

        result = agent("Read")

        assert result.stop_reason == "end_turn"
        assert executed == [True]
        mock_classifier.assert_not_called()

    def test_custom_classifier_function(self):
        executed = []

        @tool(name="deploy")
        def deploy() -> str:
            executed.append(True)
            return "deployed"

        agent_model = MockedModelProvider(
            [tool_use_message("deploy", tool_input={"env": "prod"}), text_message("Done")]
        )

        def my_classifier(event, **kwargs):
            return ClassifierResult(
                requires_human_in_the_loop=event.tool_use["name"] == "deploy",
                reason="deployment requires approval",
            )

        agent = Agent(
            model=agent_model,
            tools=[deploy],
            interventions=[HumanInTheLoop(classifier=my_classifier)],
        )

        result = agent("Deploy")

        assert result.stop_reason == "interrupt"
        assert executed == []

    def test_classifier_reason_appears_in_prompt(self):
        from unittest.mock import MagicMock

        prompts = []

        @tool(name="send_email")
        def send_email() -> str:
            return "sent"

        agent_model = MockedModelProvider(
            [tool_use_message("send_email", tool_input={"to": "all@co.com"}), text_message("Done")]
        )

        mock_classifier = MagicMock(
            return_value=ClassifierResult(requires_human_in_the_loop=True, reason="external communication")
        )

        def capture_ask(prompt, **kwargs):
            prompts.append(prompt)
            return "no"

        agent = Agent(
            model=agent_model,
            tools=[send_email],
            interventions=[HumanInTheLoop(classifier=mock_classifier, ask=capture_ask)],
        )

        agent("Send email")

        assert "external communication" in prompts[0]
        assert "send_email" in prompts[0]

    def test_async_custom_classifier(self):
        import asyncio

        executed = []

        @tool(name="deploy")
        def deploy() -> str:
            executed.append(True)
            return "deployed"

        agent_model = MockedModelProvider(
            [tool_use_message("deploy", tool_input={"env": "prod"}), text_message("Done")]
        )

        async def my_classifier(event, **kwargs):
            return ClassifierResult(
                requires_human_in_the_loop=True,
                reason="async classifier says no",
            )

        agent = Agent(
            model=agent_model,
            tools=[deploy],
            interventions=[HumanInTheLoop(classifier=my_classifier)],
        )

        result = agent("Deploy")

        assert result.stop_reason == "interrupt"
        assert executed == []

    def test_classifier_error_fails_closed(self):
        executed = []

        @tool(name="my_tool")
        def my_tool() -> str:
            executed.append(True)
            return "ran"

        def broken_classifier(event, **kwargs):
            raise RuntimeError("model down")

        agent_model = MockedModelProvider([tool_use_message("my_tool"), text_message("Done")])
        agent = Agent(
            model=agent_model,
            tools=[my_tool],
            interventions=[HumanInTheLoop(classifier=broken_classifier)],
        )

        result = agent("Go")

        assert result.stop_reason == "interrupt"
        assert executed == []

    def test_malformed_classifier_result_fails_closed(self):
        from types import SimpleNamespace

        executed = []

        @tool(name="my_tool")
        def my_tool() -> str:
            executed.append(True)
            return "ran"

        def bad_classifier(event, **kwargs):
            return SimpleNamespace(requires_human_in_the_loop=None)

        agent_model = MockedModelProvider([tool_use_message("my_tool"), text_message("Done")])
        agent = Agent(
            model=agent_model,
            tools=[my_tool],
            interventions=[HumanInTheLoop(classifier=bad_classifier)],
        )

        result = agent("Go")

        assert result.stop_reason == "interrupt"
        assert executed == []

    def test_classifier_not_called_on_resume(self):

        executed = []
        call_count = []

        @tool(name="my_tool")
        def my_tool() -> str:
            executed.append(True)
            return "ran"

        def counting_classifier(event, **kwargs):
            call_count.append(1)
            return ClassifierResult(requires_human_in_the_loop=True, reason="risky")

        agent_model = MockedModelProvider([tool_use_message("my_tool"), text_message("Done")])
        agent = Agent(
            model=agent_model,
            tools=[my_tool],
            interventions=[HumanInTheLoop(classifier=counting_classifier)],
        )

        result = agent("Go")
        assert result.stop_reason == "interrupt"
        assert len(call_count) == 1

        interrupt_id = result.interrupts[0].id
        result = agent([{"interruptResponse": {"interruptId": interrupt_id, "response": "y"}}])
        assert result.stop_reason == "end_turn"
        assert executed == [True]
        # Classifier was only called once (not again on resume)
        assert len(call_count) == 1


class TestPublicExports:
    """Public API exports: HumanInTheLoop, HumanInTheLoopClassifier, LLMClassifierConfig."""

    def test_public_exports(self):
        import strands.vended_interventions as vended
        import strands.vended_interventions.hitl as hitl

        assert vended.__all__ == ["CedarAuthorization", "HumanInTheLoop"]
        assert hitl.__all__ == ["HumanInTheLoop", "HumanInTheLoopClassifier", "LLMClassifierConfig"]
        assert vended.HumanInTheLoop is hitl.HumanInTheLoop
        assert hitl.HumanInTheLoop.name == "strands:human-in-the-loop"
