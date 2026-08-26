import unittest

from agentscope.agent import Agent
from agentscope.agent._config import ModelConfig, ContextConfig, ReActConfig
from tests.utils import MockModel


class TestAgentConfigIsolation(unittest.TestCase):
    def test_default_config_instances_are_unique_per_agent(self):
        """Test that default config objects are not shared between Agent instances."""

        agent1 = Agent(
            name="agent1",
            system_prompt="You are agent 1.",
            model=MockModel(),
        )
        agent2 = Agent(
            name="agent2",
            system_prompt="You are agent 2.",
            model=MockModel(),
        )

        # Check that the config objects are not the same instance (no sharing)
        self.assertIsNot(agent1.model_config, agent2.model_config)
        self.assertIsNot(agent1.context_config, agent2.context_config)
        self.assertIsNot(agent1.react_config, agent2.react_config)

        # Mutate agent1's configs and verify agent2's configs are unaffected
        # Use only existing fields on the config classes to avoid ValueError
        # ModelConfig has max_retries and fallback_model
        agent1.model_config.max_retries = 3
        agent2.model_config.max_retries = 0
        self.assertNotEqual(agent1.model_config.max_retries, agent2.model_config.max_retries)

        # ContextConfig has tool_result_limit
        agent1.context_config.tool_result_limit = 123
        agent2.context_config.tool_result_limit = 0
        self.assertNotEqual(agent1.context_config.tool_result_limit, agent2.context_config.tool_result_limit)

        # ReActConfig has max_iters
        agent1.react_config.max_iters = 2
        agent2.react_config.max_iters = 0
        self.assertNotEqual(agent1.react_config.max_iters, agent2.react_config.max_iters)

    def test_explicitly_passing_configs_results_in_shared_instances(self):
        """Test that passing the same config instances explicitly causes sharing."""

        shared_model_config = ModelConfig()
        shared_context_config = ContextConfig()
        shared_react_config = ReActConfig()

        agent1 = Agent(
            name="agent1",
            system_prompt="You are agent 1.",
            model=MockModel(),
            model_config=shared_model_config,
            context_config=shared_context_config,
            react_config=shared_react_config,
        )
        agent2 = Agent(
            name="agent2",
            system_prompt="You are agent 2.",
            model=MockModel(),
            model_config=shared_model_config,
            context_config=shared_context_config,
            react_config=shared_react_config,
        )

        # These should be the same instances because explicitly passed
        self.assertIs(agent1.model_config, agent2.model_config)
        self.assertIs(agent1.context_config, agent2.context_config)
        self.assertIs(agent1.react_config, agent2.react_config)

        # Mutate agent1's config and verify agent2's config is affected (shared)
        agent1.model_config.max_retries = 5
        agent1.context_config.tool_result_limit = 999
        agent1.react_config.max_iters = 7

        self.assertEqual(agent2.model_config.max_retries, 5)
        self.assertEqual(agent2.context_config.tool_result_limit, 999)
        self.assertEqual(agent2.react_config.max_iters, 7)


if __name__ == "__main__":
    unittest.main()
