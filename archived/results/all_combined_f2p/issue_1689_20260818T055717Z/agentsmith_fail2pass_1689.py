import asyncio
import pytest
from typing import Awaitable

from strands.plugins import Plugin


def test_plugin_protocol_sync_implementation():
    """Test that a synchronous Plugin implementation matches the Plugin Protocol."""

    class SyncPlugin:
        name = "sync-plugin"

        def __init__(self):
            self.initialized = False

        def init_plugin(self, agent) -> None:
            self.initialized = True
            agent.plugin_initialized = True

    plugin = SyncPlugin()
    mock_agent = type("AgentMock", (), {})()

    # Protocol check
    assert isinstance(plugin, Plugin)
    assert plugin.name == "sync-plugin"

    # Call init_plugin synchronously
    result = plugin.init_plugin(mock_agent)
    assert result is None
    assert plugin.initialized is True
    assert getattr(mock_agent, "plugin_initialized", False) is True


@pytest.mark.asyncio
async def test_plugin_protocol_async_implementation():
    """Test that an asynchronous Plugin implementation matches the Plugin Protocol."""

    class AsyncPlugin:
        name = "async-plugin"

        def __init__(self):
            self.initialized = False

        async def init_plugin(self, agent) -> Awaitable[None]:
            await asyncio.sleep(0)  # simulate async work
            self.initialized = True
            agent.async_plugin_initialized = True

    plugin = AsyncPlugin()
    mock_agent = type("AgentMock", (), {})()

    # Protocol check
    assert isinstance(plugin, Plugin)
    assert plugin.name == "async-plugin"

    # Call init_plugin asynchronously
    result = plugin.init_plugin(mock_agent)
    # result should be awaitable
    assert asyncio.iscoroutine(result)
    await result
    assert plugin.initialized is True
    assert getattr(mock_agent, "async_plugin_initialized", False) is True


def test_plugin_protocol_requires_name_and_init_plugin():
    """Test that objects missing 'name' or 'init_plugin' do not match the Plugin Protocol."""

    class MissingName:
        def init_plugin(self, agent):
            pass

    class MissingInitPlugin:
        name = "missing-init"

    missing_name = MissingName()
    missing_init = MissingInitPlugin()

    assert not isinstance(missing_name, Plugin)
    assert not isinstance(missing_init, Plugin)


def test_plugin_protocol_with_property_name():
    """Test Plugin Protocol works when 'name' is a property."""

    class PluginWithPropertyName:
        @property
        def name(self):
            return "property-plugin"

        def init_plugin(self, agent):
            agent.prop_init = True

    plugin = PluginWithPropertyName()
    mock_agent = type("AgentMock", (), {})()

    assert isinstance(plugin, Plugin)
    assert plugin.name == "property-plugin"

    result = plugin.init_plugin(mock_agent)
    assert result is None
    assert getattr(mock_agent, "prop_init", False) is True
