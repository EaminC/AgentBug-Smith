from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from typing import Any, AsyncGenerator, Awaitable, Callable

from agentscope.agent import Agent
from agentscope.middleware import MiddlewareBase
from agentscope.message import ToolCallBlock, ToolCallState, TextBlock
from agentscope.permission import PermissionDecision, PermissionBehavior, PermissionContext
from agentscope.tool import Toolkit, ToolBase, ToolChunk


class TestCheckPermissionMiddleware(IsolatedAsyncioTestCase):
    """Test the permission-checking middleware onion."""

    async def asyncSetUp(self) -> None:
        """Set up permission middleware test fixtures."""
        self.mock_model = AsyncMock()
        self.mock_model._call_api = AsyncMock()
        self.execution_log: list[str] = []

    async def test_on_check_permission_middleware_detection(self) -> None:
        """Only middleware overriding the permission hook is selected."""

        class CheckPermissionMiddleware(MiddlewareBase):
            """Middleware implementing only the permission hook."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                """Delegate permission checking unchanged."""
                return await next_handler(**input_kwargs)

        self.assertFalse(
            MiddlewareBase().is_implemented("on_check_permission"),
        )
        self.assertTrue(
            CheckPermissionMiddleware().is_implemented(
                "on_check_permission",
            ),
        )

    async def test_on_check_permission_without_middleware_calls_engine(
        self,
    ) -> None:
        """The no-middleware path preserves the direct engine call."""
        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
        )
        tool = AsyncMock(spec=ToolBase)
        tool_input = {"value": "original"}
        expected = PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="allowed",
        )
        engine = AsyncMock(return_value=expected)

        with patch.object(agent._engine, "check_permission", new=engine):
            actual = await agent._check_permission(
                ToolCallBlock(id="call_permission", name="tool", input="{}"),
                tool,
                tool_input,
            )

        self.assertIs(actual, expected)
        engine.assert_awaited_once_with(tool, tool_input)

    async def test_on_check_permission_follows_onion_order(self) -> None:
        """Permission middleware wraps the engine in registration order."""

        class PermissionTool(ToolBase):
            """Minimal tool used to exercise permission checking."""

            name = "permission_tool"
            description = "A tool used by permission middleware tests."
            input_schema = {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            }
            is_concurrency_safe = True
            is_read_only = False

            async def check_permissions(
                self,
                tool_input: dict[str, Any],
                context: PermissionContext,
            ) -> PermissionDecision:
                """Return a regular ASK when exercised without a mock."""
                return PermissionDecision(
                    behavior=PermissionBehavior.ASK,
                    message="permission required",
                )

        class OrderedMiddleware(MiddlewareBase):
            """Record before and after delegating to the next layer."""

            def __init__(self, name: str) -> None:
                self.name = name

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                self_outer.execution_log.append(f"{self.name}_pre")
                self_outer.assertEqual(
                    set(input_kwargs),
                    {"tool_call", "tool", "tool_input"},
                )
                decision = await next_handler(**input_kwargs)
                self_outer.execution_log.append(f"{self.name}_post")
                return decision

        self_outer = self
        tool = PermissionTool()
        tool_call = ToolCallBlock(
            id="call_permission",
            name=tool.name,
            input='{"value": "original"}',
        )
        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
            toolkit=Toolkit(tools=[tool]),
            middlewares=[OrderedMiddleware("mw1"), OrderedMiddleware("mw2")],
        )
        engine_decision = PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="allowed by engine",
        )

        async def check_permission(
            checked_tool: ToolBase,
            checked_input: dict,
        ) -> PermissionDecision:
            self.execution_log.append("engine")
            self.assertIs(checked_tool, tool)
            self.assertEqual(checked_input, {"value": "original"})
            return engine_decision

        with patch.object(
            agent._engine,  # pylint: disable=protected-access
            "check_permission",
            side_effect=check_permission,
        ):
            decision = await agent._check_permission(
                tool_call,
                tool,
                {"value": "original"},
            )

        self.assertIs(decision, engine_decision)
        self.assertListEqual(
            self.execution_log,
            ["mw1_pre", "mw2_pre", "engine", "mw2_post", "mw1_post"],
        )

    async def test_on_check_permission_observes_final_engine_decisions(
        self,
    ) -> None:
        """The hook observes each final behavior returned by the engine."""

        class ObserveMiddleware(MiddlewareBase):
            """Record and preserve the engine's final decision."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                decision = await next_handler(**input_kwargs)
                observed.append(decision.behavior)
                return decision

        observed: list[PermissionBehavior] = []
        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
            middlewares=[ObserveMiddleware()],
        )
        tool = AsyncMock(spec=ToolBase)
        tool_call = ToolCallBlock(
            id="call_permission",
            name="permission_tool",
            input="{}",
        )

        for behavior in (
            PermissionBehavior.ALLOW,
            PermissionBehavior.ASK,
            PermissionBehavior.DENY,
        ):
            engine_decision = PermissionDecision(
                behavior=behavior,
                message=behavior.value,
            )
            with patch.object(
                agent._engine,  # pylint: disable=protected-access
                "check_permission",
                new=AsyncMock(return_value=engine_decision),
            ):
                decision = await agent._check_permission(
                    tool_call,
                    tool,
                    {},
                )
            self.assertIs(decision, engine_decision)

        self.assertListEqual(
            observed,
            [
                PermissionBehavior.ALLOW,
                PermissionBehavior.ASK,
                PermissionBehavior.DENY,
            ],
        )

    async def test_on_check_permission_can_replace_decision(self) -> None:
        """Post-processing may replace the engine decision."""

        replacement = PermissionDecision(
            behavior=PermissionBehavior.DENY,
            message="denied by application policy",
        )

        class ReplaceMiddleware(MiddlewareBase):
            """Replace the built-in engine result after observing it."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                await next_handler(**input_kwargs)
                return replacement

        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
            middlewares=[ReplaceMiddleware()],
        )
        engine = AsyncMock(
            return_value=PermissionDecision(
                behavior=PermissionBehavior.ALLOW,
                message="allowed by engine",
            ),
        )
        with patch.object(
            agent._engine,  # pylint: disable=protected-access
            "check_permission",
            new=engine,
        ):
            decision = await agent._check_permission(
                ToolCallBlock(id="call_permission", name="tool", input="{}"),
                AsyncMock(spec=ToolBase),
                {},
            )

        engine.assert_awaited_once()
        self.assertIs(decision, replacement)

    async def test_on_check_permission_can_short_circuit(self) -> None:
        """A middleware may return a decision without running the engine."""

        short_circuit = PermissionDecision(
            behavior=PermissionBehavior.DENY,
            message="tenant policy denied the call",
        )

        class TenantPolicyMiddleware(MiddlewareBase):
            """Deny without delegating to the built-in engine."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                return short_circuit

        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
            middlewares=[TenantPolicyMiddleware()],
        )
        engine = AsyncMock()
        with patch.object(
            agent._engine,  # pylint: disable=protected-access
            "check_permission",
            new=engine,
        ):
            decision = await agent._check_permission(
                ToolCallBlock(id="call_permission", name="tool", input="{}"),
                AsyncMock(spec=ToolBase),
                {},
            )

        engine.assert_not_awaited()
        self.assertIs(decision, short_circuit)

    async def test_on_check_permission_forwards_replaced_input(
        self,
    ) -> None:
        """Explicitly forwarded inputs reach downstream permission checks."""

        forwarded_input = {"value": "original"}
        seen_by_inner: list[dict[str, str]] = []

        class ForwardingMiddleware(MiddlewareBase):
            """Replace the chain-local input with an equivalent object."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                return await next_handler(
                    **{
                        **input_kwargs,
                        "tool_input": forwarded_input,
                    },
                )

        class ObserveInnerMiddleware(MiddlewareBase):
            """Record the input forwarded by the outer middleware."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                seen_by_inner.append(input_kwargs["tool_input"])
                return await next_handler(**input_kwargs)

        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
            middlewares=[ForwardingMiddleware(), ObserveInnerMiddleware()],
        )
        tool = AsyncMock(spec=ToolBase)
        tool_call = ToolCallBlock(
            id="call_permission",
            name="tool",
            input='{"value": "original"}',
        )
        tool_input = {"value": "original"}
        engine = AsyncMock(
            return_value=PermissionDecision(
                behavior=PermissionBehavior.ALLOW,
                message="allowed",
            ),
        )
        with patch.object(
            agent._engine,  # pylint: disable=protected-access
            "check_permission",
            new=engine,
        ):
            await agent._check_permission(  # pylint: disable=protected-access
                tool_call,
                tool,
                tool_input,
            )

        self.assertEqual(tool_call.input, '{"value": "original"}')
        self.assertEqual(tool_input, {"value": "original"})
        self.assertIs(seen_by_inner[0], forwarded_input)
        engine.assert_awaited_once_with(tool, forwarded_input)

    async def test_on_check_permission_exception_propagates(self) -> None:
        """Permission middleware failures propagate to the caller."""

        class FailingMiddleware(MiddlewareBase):
            """Raise before delegating permission checking."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                raise RuntimeError("policy service unavailable")

        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
            middlewares=[FailingMiddleware()],
        )
        engine = AsyncMock()
        with patch.object(
            agent._engine,  # pylint: disable=protected-access
            "check_permission",
            new=engine,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "policy service unavailable",
            ):
                await agent._check_permission(
                    ToolCallBlock(
                        id="call_permission",
                        name="tool",
                        input="{}",
                    ),
                    AsyncMock(spec=ToolBase),
                    {},
                )

        engine.assert_not_awaited()

    async def test_execute_tool_call_consumes_short_circuit_decision(
        self,
    ) -> None:
        """The tool lifecycle consumes the middleware's returned decision."""

        executed: list[bool] = []

        class PermissionTool(ToolBase):
            """Tool that records whether its body was reached."""

            name = "permission_tool"
            description = "A tool used by permission middleware tests."
            input_schema = {"type": "object", "properties": {}}
            is_concurrency_safe = True
            is_read_only = False

            async def check_permissions(
                self,
                tool_input: dict[str, Any],
                context: PermissionContext,
            ) -> PermissionDecision:
                raise AssertionError("the engine should be short-circuited")

            async def call(self) -> ToolChunk:
                executed.append(True)
                return ToolChunk(content=[TextBlock(text="executed")])

        class DenyMiddleware(MiddlewareBase):
            """Deny the call before the built-in engine runs."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                return PermissionDecision(
                    behavior=PermissionBehavior.DENY,
                    message="denied by application policy",
                )

        tool = PermissionTool()
        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
            toolkit=Toolkit(tools=[tool]),
            middlewares=[DenyMiddleware()],
        )
        events = [
            event
            async for event in agent._execute_tool_call(
                ToolCallBlock(
                    id="call_permission",
                    name=tool.name,
                    input="{}",
                ),
            )
        ]

        self.assertTrue(events)
        self.assertListEqual(executed, [])

    async def test_confirmed_tool_call_runs_hook_without_rechecking_engine(
        self,
    ) -> None:
        """Application policy can override a user-confirmed ALLOW."""

        executed: list[bool] = []

        class PermissionTool(ToolBase):
            """Minimal allowed tool for the confirmation-resume path."""

            name = "permission_tool"
            description = "A tool used by permission middleware tests."
            input_schema = {"type": "object", "properties": {}}
            is_concurrency_safe = True
            is_read_only = False

            async def check_permissions(
                self,
                tool_input: dict[str, Any],
                context: PermissionContext,
            ) -> PermissionDecision:
                """The confirmed path must skip this method."""
                raise AssertionError("permission should not be rechecked")

            async def call(self) -> ToolChunk:
                executed.append(True)
                return ToolChunk(content=[TextBlock(text="executed")])

        class ObserveMiddleware(MiddlewareBase):
            """Record the confirmed decision returned by the inner handler."""

            async def on_check_permission(
                self,
                agent: Agent,
                input_kwargs: dict,
                next_handler: Callable[..., Awaitable[PermissionDecision]],
            ) -> PermissionDecision:
                decision = await next_handler(**input_kwargs)
                self_outer.execution_log.append(decision.behavior.value)
                return PermissionDecision(
                    behavior=PermissionBehavior.DENY,
                    message="application policy changed while awaiting user",
                )

        self_outer = self
        tool = PermissionTool()
        agent = Agent(
            name="test_agent",
            system_prompt="test prompt",
            model=self.mock_model,
            toolkit=Toolkit(tools=[tool]),
            middlewares=[ObserveMiddleware()],
        )
        tool_call = ToolCallBlock(
            id="call_permission",
            name=tool.name,
            input="{}",
            state=ToolCallState.ALLOWED,
        )

        events = [
            event
            async for event in agent._execute_tool_call(
                tool_call,
            )
        ]

        self.assertTrue(events)
        self.assertListEqual(self.execution_log, ["allow"])
        self.assertListEqual(executed, [])

    async def asyncTearDown(self) -> None:
        """Clean up test fixtures."""
        self.execution_log.clear()
