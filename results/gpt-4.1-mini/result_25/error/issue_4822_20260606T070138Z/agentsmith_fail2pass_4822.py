import contextvars
import time
import pytest

from crewai.task import Task

# Define a ContextVar for testing context propagation
test_var = contextvars.ContextVar("test_var", default=None)

class DummyAgent:
    # Minimal stub for agent argument
    pass

class DummyTools:
    # Minimal stub for tools argument
    pass

def dummy_task_execution(self, agent, context, tools, future):
    """
    Replacement for _execute_task_async that reads the ContextVar and sets the Future result.
    """
    try:
        # Read the ContextVar inside the thread
        value = test_var.get()
        # Set the Future result to the value read from ContextVar
        future.set_result(value)
    except Exception as e:
        future.set_exception(e)

@pytest.mark.timeout(5)
def test_async_execution_preserves_contextvar():
    """
    This test verifies that when execute_async is called with async_execution=True,
    the ContextVar set on the calling thread is visible inside the worker thread.

    Before the fix, the ContextVar value inside the worker thread is None (default).
    After the fix, the ContextVar value inside the worker thread is preserved ("hello").
    """
    # Set the ContextVar on the main thread
    test_var.set("hello")

    # Create a Task instance
    task = Task()

    # Patch the _execute_task_async method to our dummy that reads ContextVar and sets Future result
    # We do not mock execute_async itself, only the internal method it calls
    original_execute_task_async = task._execute_task_async
    task._execute_task_async = dummy_task_execution.__get__(task, Task)

    # Call execute_async with dummy agent, context, and tools
    future = task.execute_async(DummyAgent(), {}, DummyTools())

    # Wait for the future to complete with timeout
    timeout = 3.0
    start = time.monotonic()
    while not future.done():
        if time.monotonic() - start > timeout:
            pytest.fail("Future did not complete within timeout")
        time.sleep(0.01)

    # Get the result from the future
    result = future.result()

    # Restore the original method to avoid side effects
    task._execute_task_async = original_execute_task_async

    # Assert that the ContextVar value was preserved inside the worker thread
    # Before fix: result == None (default)
    # After fix: result == "hello"
    assert result == "hello", (
        "ContextVar value was not preserved inside async_execution worker thread. "
        "This indicates the bug is present."
    )