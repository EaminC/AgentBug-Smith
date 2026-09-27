from strands import Agent
from strands.hooks.events import BeforeInvocationEvent
from strands.vended_plugins.skills.agent_skills import AgentSkills
from strands.vended_plugins.skills.skill import Skill


def test_agent_skills_preserves_cache_points_in_system_prompt():
    """
    End-to-end test that the AgentSkills plugin injects skills XML into a structured system prompt,
    preserving cache points, and that the agent.system_prompt_content reflects this after invocation.
    """
    # Create a skill and the AgentSkills plugin
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    # Create an agent with a structured system prompt including cachePoint
    initial_system_prompt_content = [
        {"text": "Base instructions."},
        {"cachePoint": {"type": "default"}},
        {"text": "More instructions."},
    ]
    agent = Agent(
        system_prompt=initial_system_prompt_content,
        plugins=[plugin],
    )

    # Save the initial _system_prompt_content for comparison
    before_invocation_content = list(agent._system_prompt_content)

    # Sanity check: before invocation, the system prompt content matches the initial structured blocks
    assert before_invocation_content == initial_system_prompt_content

    # Create a BeforeInvocationEvent and call the plugin's _on_before_invocation hook
    event = BeforeInvocationEvent(agent=agent)
    plugin._on_before_invocation(event)

    # After the hook runs, the system prompt content should still be a list of blocks,
    # preserving the cachePoint block and the original text blocks, plus the injected skills XML block.
    after_invocation_content = agent._system_prompt_content

    # Check that the after_invocation_content is a list
    assert isinstance(after_invocation_content, list)

    # The first two blocks should be the original ones: text and cachePoint
    assert after_invocation_content[0] == {"text": "Base instructions."}
    assert after_invocation_content[1] == {"cachePoint": {"type": "default"}}

    # The last block should be the injected skills XML containing the skill name
    assert "my-skill" in after_invocation_content[-1].get("text", "")

    # The length should be original length + 1 (injected block)
    assert len(after_invocation_content) == len(before_invocation_content) + 1


def test_agent_skills_plugin_injects_skills_xml_and_preserves_cache_points():
    """
    Test that the AgentSkills plugin injects skills XML into the system prompt string,
    appending it correctly and preserving the original prompt text.
    """
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    base_prompt = "Base instructions."
    agent = Agent(system_prompt=base_prompt, plugins=[plugin])

    # Before invocation, system_prompt is the base prompt string
    assert agent.system_prompt == base_prompt
    assert agent._system_prompt_content == [{"text": base_prompt}]

    event = BeforeInvocationEvent(agent=agent)
    plugin._on_before_invocation(event)

    # After invocation, system_prompt is a string containing the base prompt and injected skills XML
    new_prompt = agent.system_prompt
    assert new_prompt.startswith(base_prompt)
    assert "<available_skills>" in new_prompt
    assert "<name>my-skill</name>" in new_prompt

    # The internal _system_prompt_content is a list with two text blocks: original and injected
    assert isinstance(agent._system_prompt_content, list)
    assert len(agent._system_prompt_content) == 2
    assert agent._system_prompt_content[0] == {"text": base_prompt}
    assert "<available_skills>" in agent._system_prompt_content[1]["text"]


def test_agent_skills_plugin_injection_does_not_flatten_cache_points():
    """
    This test ensures that after the AgentSkills plugin injects skills XML,
    the agent._system_prompt_content remains a list of content blocks,
    preserving cachePoint blocks instead of flattening to a single text block.
    """
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    # Structured system prompt with cachePoint
    initial_prompt = [
        {"text": "Base instructions."},
        {"cachePoint": {"type": "default"}},
        {"text": "More instructions."},
    ]
    agent = Agent(system_prompt=initial_prompt, plugins=[plugin])

    # Before invocation, _system_prompt_content is structured
    assert agent._system_prompt_content == initial_prompt

    # Trigger the plugin hook that injects skills XML
    event = BeforeInvocationEvent(agent=agent)
    plugin._on_before_invocation(event)

    # After invocation, _system_prompt_content should still be a list with cachePoint preserved
    content_after = agent._system_prompt_content
    assert isinstance(content_after, list)

    # There should be a cachePoint block preserved
    assert any("cachePoint" in block for block in content_after)

    # The last block should be the injected skills XML
    assert "<available_skills>" in content_after[-1].get("text", "")


def test_agent_skills_plugin_injection_uses_public_system_prompt_setter():
    """
    Test that the AgentSkills plugin uses the public system_prompt setter when injecting skills XML,
    ensuring _system_prompt_content is consistent with _system_prompt.
    """
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    agent = Agent(system_prompt="Original.", plugins=[plugin])
    event = BeforeInvocationEvent(agent=agent)

    plugin._on_before_invocation(event)

    # The _system_prompt_content should be a list with original block and injected XML block
    content = agent._system_prompt_content
    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0] == {"text": "Original."}
    assert "<available_skills>" in content[1]["text"]


def test_agent_skills_plugin_injection_repeated_invocations_do_not_accumulate():
    """
    Test that repeated invocations of the AgentSkills plugin's _on_before_invocation
    do not accumulate multiple injected XML blocks.
    """
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    initial_prompt = [
        {"text": "Base instructions."},
        {"cachePoint": {"type": "default"}},
    ]
    agent = Agent(system_prompt=initial_prompt, plugins=[plugin])

    event = BeforeInvocationEvent(agent=agent)

    plugin._on_before_invocation(event)
    first_content = list(agent._system_prompt_content)

    plugin._on_before_invocation(event)
    second_content = list(agent._system_prompt_content)

    # The content should be identical after repeated invocations
    assert first_content == second_content

    # There should be exactly one injected skills XML block appended
    assert len(first_content) == len(initial_prompt) + 1
    assert "<available_skills>" in first_content[-1].get("text", "")


def test_agent_skills_plugin_injection_on_none_system_prompt():
    """
    Test that the AgentSkills plugin handles None system prompt gracefully,
    injecting the skills XML as the only system prompt content.
    """
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    agent = Agent(system_prompt=None, plugins=[plugin])
    event = BeforeInvocationEvent(agent=agent)

    plugin._on_before_invocation(event)

    content = agent._system_prompt_content
    assert isinstance(content, list)
    assert len(content) == 1
    assert "<available_skills>" in content[0].get("text", "")


def test_agent_skills_plugin_injection_warns_when_previous_xml_not_found(caplog):
    """
    Test that a warning is logged when the previously injected XML is missing from the system prompt.
    """
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    agent = Agent(system_prompt="Original prompt.", plugins=[plugin])
    event = BeforeInvocationEvent(agent=agent)

    # First injection to set last_injected_xml state
    plugin._on_before_invocation(event)

    # Replace system prompt with a new string that does not contain the injected XML
    agent.system_prompt = "Totally new prompt."
    agent._system_prompt_content = [{"text": "Totally new prompt."}]

    with caplog.at_level("WARNING"):
        plugin._on_before_invocation(event)

    assert "unable to find previously injected skills XML in system prompt" in caplog.text
    assert "<available_skills>" in agent.system_prompt


def test_agent_skills_plugin_injection_on_string_path_replaces_previous_xml():
    """
    Test that when system_prompt_content is None (string path),
    the plugin replaces the old injected XML correctly.
    """
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    old_xml = "\n\n<old>xml</old>"
    agent = Agent(system_prompt=f"Base prompt.{old_xml}", plugins=[plugin])
    agent._system_prompt_content = None
    agent.state.set(plugin._state_key, {"last_injected_xml": old_xml})

    event = BeforeInvocationEvent(agent=agent)
    plugin._on_before_invocation(event)

    # The old XML should be removed and replaced by new skills XML
    assert "<old>xml</old>" not in agent.system_prompt
    assert "<available_skills>" in agent.system_prompt
    assert agent.system_prompt.startswith("Base prompt.")


def test_agent_skills_plugin_injection_on_string_path_warns_when_previous_xml_not_found(caplog):
    """
    Test that a warning is logged when the old injected XML is not found in the string system prompt.
    """
    skill = Skill(name="my-skill", description="A skill", instructions="Do the thing")
    plugin = AgentSkills(skills=[skill])

    agent = Agent(system_prompt="Totally new prompt.", plugins=[plugin])
    agent._system_prompt_content = None
    agent.state.set(plugin._state_key, {"last_injected_xml": "\n\n<old>xml</old>"})

    event = BeforeInvocationEvent(agent=agent)
    with caplog.at_level("WARNING"):
        plugin._on_before_invocation(event)

    assert "unable to find previously injected skills XML in system prompt" in caplog.text
    assert "<available_skills>" in agent.system_prompt
