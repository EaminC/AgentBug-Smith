from crewai.agent import Agent
from crewai.project import agent, task
from crewai.task import Task


class TestAsyncDecoratorSupport:
    """Tests for async method support in @agent, @task decorators."""

    def test_async_agent_memoization(self):
        """Async agent methods should be properly memoized."""

        class AsyncAgentCrew:
            call_count = 0

            @agent
            async def async_agent(self):
                AsyncAgentCrew.call_count += 1
                return Agent(
                    role="Async Agent", goal="Async Goal", backstory="Async Backstory"
                )

        crew = AsyncAgentCrew()
        first_call = crew.async_agent()
        second_call = crew.async_agent()

        assert first_call is second_call, "Async agent memoization failed"
        assert AsyncAgentCrew.call_count == 1, "Async agent called more than once"

    def test_async_task_memoization(self):
        """Async task methods should be properly memoized."""

        class AsyncTaskCrew:
            call_count = 0

            @task
            async def async_task(self):
                AsyncTaskCrew.call_count += 1
                return Task(
                    description="Async Description", expected_output="Async Output"
                )

        crew = AsyncTaskCrew()
        first_call = crew.async_task()
        second_call = crew.async_task()

        assert first_call is second_call, "Async task memoization failed"
        assert AsyncTaskCrew.call_count == 1, "Async task called more than once"

    def test_async_task_name_inference(self):
        """Async task should have name inferred from method name."""

        class AsyncTaskNameCrew:
            @task
            async def my_async_task(self):
                return Task(
                    description="Async Description", expected_output="Async Output"
                )

        crew = AsyncTaskNameCrew()
        task_instance = crew.my_async_task()

        assert task_instance.name == "my_async_task", (
            "Async task name not inferred correctly"
        )

    def test_async_agent_returns_agent_not_coroutine(self):
        """Async agent decorator should return Agent, not coroutine."""

        class AsyncAgentTypeCrew:
            @agent
            async def typed_async_agent(self):
                return Agent(
                    role="Typed Agent", goal="Typed Goal", backstory="Typed Backstory"
                )

        crew = AsyncAgentTypeCrew()
        result = crew.typed_async_agent()

        assert isinstance(result, Agent), (
            f"Expected Agent, got {type(result).__name__}"
        )

    def test_async_task_returns_task_not_coroutine(self):
        """Async task decorator should return Task, not coroutine."""

        class AsyncTaskTypeCrew:
            @task
            async def typed_async_task(self):
                return Task(
                    description="Typed Description", expected_output="Typed Output"
                )

        crew = AsyncTaskTypeCrew()
        result = crew.typed_async_task()

        assert isinstance(result, Task), f"Expected Task, got {type(result).__name__}"
