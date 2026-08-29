import asyncio
from unittest import IsolatedAsyncioTestCase

import fakeredis.aioredis

from agentscope.app._tools._agent_create import AgentCreate, DEFAULT_SUB_AGENT_TEMPLATE
from agentscope.app._types import SubAgentTemplate
from agentscope.permission import PermissionContext, PermissionMode, PermissionRule, PermissionBehavior, AdditionalWorkingDirectory
from agentscope.state import AgentState
from agentscope.app.storage import RedisStorage, SessionConfig, AgentRecord, AgentData
from agentscope.app.message_bus import RedisMessageBus
from agentscope.agent import ContextConfig, ReActConfig


def _make_storage(fr: fakeredis.aioredis.FakeRedis) -> RedisStorage:
    class _S(RedisStorage):
        async def __aenter__(self) -> "RedisStorage":
            self._client = fr
            return self

        async def aclose(self) -> None:
            self._client = None

    return _S()


def _make_bus(fr: fakeredis.aioredis.FakeRedis) -> RedisMessageBus:
    class _B(RedisMessageBus):
        async def __aenter__(self) -> "RedisMessageBus":
            self._client = fr
            return self

        async def aclose(self) -> None:
            self._client = None

    return _B()


def _make_agent_record(user_id: str, name: str, source: str = "user") -> AgentRecord:
    return AgentRecord(
        user_id=user_id,
        source=source,
        data=AgentData(
            name=name,
            system_prompt=f"You are {name}.",
            context_config=ContextConfig(),
            react_config=ReActConfig(),
        ),
    )


class TestAgentCreatePermissionInheritance(IsolatedAsyncioTestCase):
    """Test that AgentCreate copies permission rules from leader to sub-agent."""

    async def asyncSetUp(self) -> None:
        self.fr = fakeredis.aioredis.FakeRedis(decode_responses=True)
        self.storage = await _make_storage(self.fr).__aenter__()
        self.bus = await _make_bus(self.fr).__aenter__()

        # Create leader agent and session
        self.user_id = "user1"
        self.leader_agent = _make_agent_record(self.user_id, "leader")
        await self.storage.upsert_agent(self.user_id, self.leader_agent)
        self.leader_session = await self.storage.upsert_session(
            user_id=self.user_id,
            agent_id=self.leader_agent.id,
            config=SessionConfig(workspace_id="ws"),
        )

        # Create a team for the leader session so AgentCreate can add members
        from agentscope.app._tools._team_create import TeamCreate
        team_create_tool = TeamCreate(
            storage=self.storage,
            message_bus=self.bus,
            user_id=self.user_id,
            session_id=self.leader_session.id,
            agent_id=self.leader_agent.id,
        )
        await team_create_tool(name="team", description="desc")

    async def asyncTearDown(self) -> None:
        await self.storage.aclose()
        await self.bus.aclose()
        await self.fr.aclose()

    def _make_leader_state(self) -> AgentState:
        """Create a leader AgentState with permission context including mode, rules, and working dirs."""
        return AgentState(
            permission_context=PermissionContext(
                mode=PermissionMode.ACCEPT_EDITS,
                working_directories={
                    "/tmp/as-workspace": AdditionalWorkingDirectory(
                        path="/tmp/as-workspace",
                        source="session",
                    ),
                },
                allow_rules={
                    "Bash": [
                        PermissionRule(
                            tool_name="Bash",
                            rule_content="git status",
                            behavior=PermissionBehavior.ALLOW,
                            source="session",
                        ),
                    ],
                },
                deny_rules={
                    "Write": [
                        PermissionRule(
                            tool_name="Write",
                            rule_content=None,
                            behavior=PermissionBehavior.DENY,
                            source="session",
                        ),
                    ],
                },
                ask_rules={
                    "Read": [
                        PermissionRule(
                            tool_name="Read",
                            rule_content="secret.txt",
                            behavior=PermissionBehavior.ASK,
                            source="session",
                        ),
                    ],
                },
            ),
        )

    async def _spawn_worker_with_template(
        self,
        leader_state: AgentState,
        template: SubAgentTemplate,
        worker_name: str = "worker",
    ) -> PermissionContext:
        """Run AgentCreate with given template and leader state, return worker's permission context."""
        tool = AgentCreate(
            storage=self.storage,
            message_bus=self.bus,
            user_id=self.user_id,
            session_id=self.leader_session.id,
            agent_id=self.leader_agent.id,
            sub_agent_templates={template.type: template},
        )
        chunk = await tool(
            name=worker_name,
            description="does work",
            prompt="work in the repo",
            subagent_type=template.type,
            _agent_state=leader_state,
        )
        self.assertEqual(chunk.state.value, "running")
        sess = await self.storage.get_session(
            self.user_id,
            self.leader_agent.id,
            self.leader_session.id,
        )
        team = await self.storage.get_team(self.user_id, sess.team_id)
        worker_agent_id = team.data.member_ids[-1]
        worker_sessions = await self.storage.list_sessions(
            self.user_id,
            worker_agent_id,
        )
        return worker_sessions[0].state.permission_context

    async def test_default_template_inherits_leader_permissions(self) -> None:
        """Default template inherits leader's mode, rules, and working directories."""
        leader_state = self._make_leader_state()
        worker_context = await self._spawn_worker_with_template(
            leader_state,
            DEFAULT_SUB_AGENT_TEMPLATE,
        )
        # Mode inherited
        self.assertEqual(worker_context.mode, PermissionMode.ACCEPT_EDITS)
        # Working directory inherited
        self.assertIn("/tmp/as-workspace", worker_context.working_directories)
        # Allow rules inherited
        self.assertIn("Bash", worker_context.allow_rules)
        self.assertEqual(worker_context.allow_rules["Bash"][0].rule_content, "git status")
        # Deny rules inherited
        self.assertIn("Write", worker_context.deny_rules)
        self.assertEqual(worker_context.deny_rules["Write"][0].behavior, PermissionBehavior.DENY)
        # Ask rules inherited
        self.assertIn("Read", worker_context.ask_rules)
        self.assertEqual(worker_context.ask_rules["Read"][0].rule_content, "secret.txt")

    async def test_override_leader_mode_true_pins_template_mode(self) -> None:
        """When override_leader_mode=True, template's mode overrides leader's."""
        leader_state = self._make_leader_state()
        explorer_template = SubAgentTemplate(
            type="explorer",
            description="Read-only worker.",
            system_prompt_template=DEFAULT_SUB_AGENT_TEMPLATE.system_prompt_template,
            permission_context=PermissionContext(
                mode=PermissionMode.EXPLORE,
            ),
            override_leader_mode=True,
        )
        worker_context = await self._spawn_worker_with_template(
            leader_state,
            explorer_template,
        )
        self.assertEqual(worker_context.mode, PermissionMode.EXPLORE)
        # Rules and working dirs still inherited by default
        self.assertIn("/tmp/as-workspace", worker_context.working_directories)
        self.assertIn("Bash", worker_context.allow_rules)

    async def test_extend_flags_false_isolate_template(self) -> None:
        """When extend_*=False, leader's rules and dirs are excluded from worker."""
        leader_state = self._make_leader_state()
        sandbox_template = SubAgentTemplate(
            type="sandbox",
            description="Isolated worker.",
            system_prompt_template=DEFAULT_SUB_AGENT_TEMPLATE.system_prompt_template,
            permission_context=PermissionContext(
                mode=PermissionMode.BYPASS,
                deny_rules={
                    "Write": [
                        PermissionRule(
                            tool_name="Write",
                            rule_content=None,
                            behavior=PermissionBehavior.DENY,
                            source="template",
                        ),
                    ],
                },
            ),
            override_leader_mode=True,
            extend_leader_permission_rules=False,
            extend_leader_working_directories=False,
        )
        worker_context = await self._spawn_worker_with_template(
            leader_state,
            sandbox_template,
        )
        self.assertEqual(worker_context.mode, PermissionMode.BYPASS)
        self.assertEqual(worker_context.working_directories, {})
        self.assertNotIn("Bash", worker_context.allow_rules)
        self.assertIn("Write", worker_context.deny_rules)
        self.assertEqual(worker_context.deny_rules["Write"][0].source, "template")

    async def test_template_rules_precede_leader_rules(self) -> None:
        """Template rules appear before leader rules in merged lists."""
        leader_state = AgentState(
            permission_context=PermissionContext(
                mode=PermissionMode.DEFAULT,
                allow_rules={
                    "Bash": [
                        PermissionRule(
                            tool_name="Bash",
                            rule_content="git status",
                            behavior=PermissionBehavior.ALLOW,
                            source="session",
                        ),
                    ],
                },
            ),
        )
        template = SubAgentTemplate(
            type="custom",
            description="Custom worker.",
            system_prompt_template=DEFAULT_SUB_AGENT_TEMPLATE.system_prompt_template,
            permission_context=PermissionContext(
                allow_rules={
                    "Bash": [
                        PermissionRule(
                            tool_name="Bash",
                            rule_content="ls",
                            behavior=PermissionBehavior.ALLOW,
                            source="template",
                        ),
                    ],
                },
            ),
        )
        worker_context = await self._spawn_worker_with_template(
            leader_state,
            template,
        )
        bash_rules = worker_context.allow_rules["Bash"]
        self.assertEqual([r.source for r in bash_rules], ["template", "session"])

    async def test_template_wins_on_working_directory_collision(self) -> None:
        """When leader and template declare same working directory, template wins."""
        leader_state = AgentState(
            permission_context=PermissionContext(
                working_directories={
                    "/tmp/shared": AdditionalWorkingDirectory(
                        path="/tmp/shared",
                        source="session",
                    ),
                },
            ),
        )
        template = SubAgentTemplate(
            type="custom",
            description="Custom worker.",
            system_prompt_template=DEFAULT_SUB_AGENT_TEMPLATE.system_prompt_template,
            permission_context=PermissionContext(
                working_directories={
                    "/tmp/shared": AdditionalWorkingDirectory(
                        path="/tmp/shared",
                        source="template",
                    ),
                },
            ),
        )
        worker_context = await self._spawn_worker_with_template(
            leader_state,
            template,
        )
        self.assertEqual(worker_context.working_directories["/tmp/shared"].source, "template")
