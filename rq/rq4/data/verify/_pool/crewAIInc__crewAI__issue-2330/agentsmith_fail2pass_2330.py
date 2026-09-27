import sys
import tempfile
from pathlib import Path

# Force workspace source priority
src_dir = str(Path("/app/src").resolve())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import yaml
from crewai.agent import Agent
from crewai.llm import LLM
from crewai.project import CrewBase, agent, llm


def test_agent_function_calling_llm():
    """
    Issue #2330 / PR #2336:
    When specifying function_calling_llm in agents.yaml, CrewBase must retrieve
    it from @llm decorated functions or preserve the string value, rather than
    attempting to look it up in the agents dictionary (which raises KeyError).
    """
    agents_data = {
        "researcher": {
            "role": "Researcher",
            "goal": "Research topic",
            "backstory": "Experienced researcher",
            "function_calling_llm": "custom_llm",
            "verbose": True,
        },
        "analyst": {
            "role": "Analyst",
            "goal": "Analyze data",
            "backstory": "Skilled analyst",
            "function_calling_llm": "online_llm",
            "verbose": True,
        },
    }
    tasks_data = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        agents_yaml_path = Path(tmpdir) / "agents.yaml"
        tasks_yaml_path = Path(tmpdir) / "tasks.yaml"

        with open(agents_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(agents_data, f)

        with open(tasks_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(tasks_data, f)

        @CrewBase
        class TestFCLLMCrew:
            agents_config = str(agents_yaml_path)
            tasks_config = str(tasks_yaml_path)

            @llm
            def custom_llm(self):
                return LLM(
                    model="openai/gpt-4o",
                    api_key="test-key",
                )

            @agent
            def researcher(self) -> Agent:
                return Agent(config=self.agents_config["researcher"])

            @agent
            def analyst(self) -> Agent:
                return Agent(config=self.agents_config["analyst"])

        # Pre-patch (Base commit b992ee9d...):
        # TestFCLLMCrew() -> map_all_agent_variables() tries `agents["custom_llm"]` -> KeyError: 'custom_llm' (FAILS, rc1=1)
        #
        # Post-patch (PR #2336):
        # TestFCLLMCrew() resolves custom_llm from @llm and online_llm from string fallback -> (PASSES, rc2=0)
        crew = TestFCLLMCrew()

        researcher_agent = crew.researcher()
        assert researcher_agent.function_calling_llm is not None
        assert isinstance(researcher_agent.function_calling_llm, LLM)
        assert researcher_agent.function_calling_llm.model == "openai/gpt-4o"

        analyst_agent = crew.analyst()
        assert analyst_agent.function_calling_llm is not None
        fc_llm = analyst_agent.function_calling_llm
        model_name = fc_llm.model if hasattr(fc_llm, "model") else str(fc_llm)
        assert "online_llm" in model_name