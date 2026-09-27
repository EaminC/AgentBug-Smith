import threading
from typing import Optional

import pytest
from pydantic import BaseModel

from crewai.flow.flow import Flow, start


def test_flow_copy_state_with_unpickleable_rlock():
    """Test that _copy_state handles unpickleable RLock objects.
    
    Regression test for issue #3828: Flow should not crash when state contains
    objects that cannot be deep copied (like threading.RLock).
    
    Before fix: Raises TypeError: cannot pickle '_thread.RLock' object
    After fix: Successfully creates a copy of the state
    """
    
    class StateWithRLock(BaseModel):
        counter: int = 0
        lock: Optional[threading.RLock] = None
    
    class RLockFlow(Flow[StateWithRLock]):
        @start()
        def step_1(self):
            self.state.counter += 1
    
    flow = RLockFlow(initial_state=StateWithRLock())
    flow._state.lock = threading.RLock()
    
    # This should not raise TypeError: cannot pickle '_thread.RLock' object
    copied_state = flow._copy_state()
    assert copied_state.counter == 0
    assert copied_state.lock is not None
