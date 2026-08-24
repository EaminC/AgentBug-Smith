import pytest
import pytest_asyncio
import unittest.mock

from strands.experimental.bidi import BidiAgent
from strands.experimental.bidi.models import BidiModel
from strands.experimental.bidi.types.events import BidiTextInputEvent


@pytest.fixture
def agent():
    return BidiAgent(model=unittest.mock.AsyncMock(spec=BidiModel), tools=[])


@pytest_asyncio.fixture
async def loop(agent):
    return agent._loop


@pytest.mark.asyncio
async def test_bidi_agent_loop_send_respects_event_role(loop, agent):
    agent.model.start = unittest.mock.AsyncMock()
    agent.model.send = unittest.mock.AsyncMock()
    await loop.start()
    await loop.send(BidiTextInputEvent(text="injected context", role="assistant"))
    assert agent.messages[-1] == {"role": "assistant", "content": [{"text": "injected context"}]}
