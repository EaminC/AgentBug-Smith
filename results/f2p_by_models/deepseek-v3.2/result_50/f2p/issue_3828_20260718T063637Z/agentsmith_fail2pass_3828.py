import threading
from typing import Optional

import pytest
from pydantic import BaseModel

from crewai.flow.flow import Flow, listen, start


def test_flow_copy_state_with_unpickleable_objects():
    """Test that _copy_state handles unpickleable objects like RLock.

    Regression test for issue #3828: Flow should not crash when state contains
    objects that cannot be deep copied (like threading.RLock).
    """

    class StateWithRLock(BaseModel):
        counter: int = 0
        lock: Optional[threading.RLock] = None

    class FlowWithRLock(Flow[StateWithRLock]):
        @start()
        def step_1(self):
            self.state.counter += 1

        @listen(step_1)
        def step_2(self):
            self.state.counter += 1

    flow = FlowWithRLock(initial_state=StateWithRLock())
    flow._state.lock = threading.RLock()

    copied_state = flow._copy_state()
    assert copied_state.counter == 0
    assert copied_state.lock is not None
