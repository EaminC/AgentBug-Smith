```
<file>src/agentscope/app/_tools/_agent_create.py</file>
<original>class AgentCreate(_TeamToolBase):
    """Spawn a new worker member into the team you lead."""

    name: str = "AgentCreate"

    description: str = """Add a new member to the team you lead.

## When to Use This Tool
After ``TeamCreate``, call this for each member you want on the team. \
Each call:
- Creates a worker agent dedicated to this team.
- Delivers ``prompt`` as the worker's first user message — **the worker \
starts executing it immediately**. (So DONT use ``TeamSay`` right after \
creating one agent).

## When NOT to Use This Tool
- You're not currently leading a team. Call ``TeamCreate`` first.
- The new member would duplicate an existing member's role; reuse the \
existing member via ``TeamSay`` instead.

## Effects
- Use the ``name`` you chose as ``to=<name>`` in ``TeamSay`` to direct \
messages to this member specifically. Names must be unique within the \
team (including against the leader's name); duplicates are rejected.
- Members spawned this way live only as long as the team — they are \
deleted when ``TeamDelete`` is called.

## Important
- You are responsible for organising the team, assigning tasks, collecting \
every member's report, and producing the final answer — all members report \
directly to you. Therefore, **DO NOT** encourage members to communicate with \
each other, and **AVOID** creating "integrator"-style members; both make the \
overall communication topology unnecessarily complex.
"""

    input_schema: dict = _AgentCreateParams.model_json_schema()

    def __init__(
        self,
        storage: "StorageBase",
        message_bus: "MessageBus",
        user_id: str,
        session_id: str,
        agent_id: str,
        sub_agent_templates: dict[str, SubAgentTemplate] | None = None,
    ) -> None:
        """Bind request-scoped identifiers plus sub-agent templates.

        Extends :meth:`_TeamToolBase.__init__` with an optional
        template registry. The built-in ``"default"`` template is
        always present as a fallback; developers can override it by
        registering their own template with ``type="default"``.

        When more than one template type is available (i.e. custom
        templates were registered), the tool's ``input_schema`` is
        dynamically extended with a ``subagent_type`` enum field so
        the leader agent can choose which type to create.

        Args:
            storage (`StorageBase`):
                Application storage backend.
            message_bus (`MessageBus`):
                Application message bus for inter-session delivery.
            user_id (`str`):
                The owner user id of the calling agent.
            session_id (`str`):
                The current session id of the calling agent.
            agent_id (`str`):
                The id of the agent invoking the tool.
            sub_agent_templates (`dict[str, SubAgentTemplate] | None`, \
optional):
                Template registry keyed by template type. The
                built-in ``"default"`` template is injected
                automatically if not already present.
        """
        super().__init__(storage, message_bus, user_id, session_id, agent_id)

        self._sub_agent_templates: dict[str, SubAgentTemplate] = dict(
            sub_agent_templates or {},
        )
        if "default" not in self._sub_agent_templates:
            self._sub_agent_templates["default"] = DEFAULT_SUB_AGENT_TEMPLATE

        # Only expose subagent_type when the developer registered
        # custom templates — a single "default" type is redundant in
        # the schema and would confuse the LLM.
        has_custom_templates = set(self._sub_agent_templates) != {"default"}
        if has_custom_templates:
            schema = copy.deepcopy(
                _AgentCreateParams.model_json_schema(),
            )
            type_descriptions = "\n".join(
                f"- ``{t.type!r}`` — {t.description}"
                for t in self._sub_agent_templates.values()
            )
            schema["properties"]["subagent_type"] = {
                "type": "string",
                "enum": list(self._sub_agent_templates),
                "description": (
                    "The type of sub-agent template to use. "
                    "Available types:\n\n"
                    f"{type_descriptions}\n\n"
                    "Each type has pre-configured system prompt, "
                    "permissions, and task context."
                ),
            }
            self.input_schema = schema
</original>
<patched>class AgentCreate(_TeamToolBase):
    """Spawn a new worker member into the team you lead."""

    name: str = "AgentCreate"
    is_state_injected: bool = True  # Enable state injection to access leader's permission context

    description: str = """Add a new member to the team you lead.

## When to Use This Tool
After ``TeamCreate``, call this for each member you want on the team. \
Each call:
- Creates a worker agent dedicated to this team.
- Delivers ``prompt`` as the worker's first user message — **the worker \
starts executing it immediately**. (So DONT use ``TeamSay`` right after \
creating one agent).

## When NOT to Use This Tool
- You're not currently leading a team. Call ``TeamCreate`` first.
- The new member would duplicate an existing member's role; reuse the \
existing member via ``TeamSay`` instead.

## Effects
- Use the ``name`` you chose as ``to=<name>`` in ``TeamSay`` to direct \
messages to this member specifically. Names must be unique within the \
team (including against the leader's name); duplicates are rejected.
- Members spawned this way live only as long as the team — they are \
deleted when ``TeamDelete`` is called.

## Important
- You are responsible for organising the team, assigning tasks, collecting \
every member's report, and producing the final answer — all members report \
directly to you. Therefore, **DO NOT** encourage members to communicate with \
each other, and **AVOID** creating "integrator"-style members; both make the \
overall communication topology unnecessarily complex.
"""

    input_schema: dict = _AgentCreateParams.model_json_schema()

    def __init__(
        self,
        storage: "StorageBase",
        message_bus: "MessageBus",
        user_id: str,
        session_id: str,
        agent_id: str,
        sub_agent_templates: dict[str, SubAgentTemplate] | None = None,
    ) -> None:
        """Bind request-scoped identifiers plus sub-agent templates.

        Extends :meth:`_TeamToolBase.__init__` with an optional
        template registry. The built-in ``"default"`` template is
        always present as a fallback; developers can override it by
        registering their own template with ``type="default"``.

        When more than one template type is available (i.e. custom
        templates were registered), the tool's ``input_schema`` is
        dynamically extended with a ``subagent_type`` enum field so
        the leader agent can choose which type to create.

        Args:
            storage (`StorageBase`):
                Application storage backend.
            message_bus (`MessageBus`):
                Application message bus for inter-session delivery.
            user_id (`str`):
                The owner user id of the calling agent.
            session_id (`str`):
                The current session id of the calling agent.
            agent_id (`str`):
                The id of the agent invoking the tool.
            sub_agent_templates (`dict[str, SubAgentTemplate] | None`, \
optional):
                Template registry keyed by template type. The
                built-in ``"default"`` template is injected
                automatically if not already present.
        """
        super().__init__(storage, message_bus, user_id, session_id, agent_id)

        self._sub_agent_templates: dict[str, SubAgentTemplate] = dict(
            sub_agent_templates or {},
        )
        if "default" not in self._sub_agent_templates:
            self._sub_agent_templates["default"] = DEFAULT_SUB_AGENT_TEMPLATE

        # Only expose subagent_type when the developer registered
        # custom templates — a single "default" type is redundant in
        # the schema and would confuse the LLM.
        has_custom_templates = set(self._sub_agent_templates) != {"default"}
        if has_custom_templates:
            schema = copy.deepcopy(
                _AgentCreateParams.model_json_schema(),
            )
            type_descriptions = "\n".join(
                f"- ``{t.type!r}`` — {t.description}"
                for t in self._sub_agent_templates.values()
            )
            schema["properties"]["subagent_type"] = {
                "type": "string",
                "enum": list(self._sub_agent_templates),
                "description": (
                    "The type of sub-agent template to use. "
                    "Available types:\n\n"
                    f"{type_descriptions}\n\n"
                    "Each type has pre-configured system prompt, "
                    "permissions, and task context."
                ),
            }
            self.input_schema = schema

    async def _create_sub_agent(self, params: _AgentCreateParams) -> str:
        """Create a new sub-agent, copying permission rules from the leader.

        Args:
            params (_AgentCreateParams): Parameters for sub-agent creation.

        Returns:
            str: The ID of the newly created sub-agent.
        """
        # Create the sub-agent with the permission context copied from leader
        leader_permission_context = None
        if self.is_state_injected and hasattr(self, "permission_context"):
            leader_permission_context = self.permission_context

        # Use the leader's permission context rules if available
        permission_rules = []
        if leader_permission_context:
            # Assuming leader_permission_context has a method or attribute `rules`
            permission_rules = copy.deepcopy(getattr(leader_permission_context, "rules", []))

        # Prepare sub-agent creation parameters, including permission rules
        # It's assumed the sub-agent creation accepts permission rules or context
        # This needs to align with actual sub-agent creation API
        sub_agent_template = self._sub_agent_templates.get(params.subagent_type, DEFAULT_SUB_AGENT_TEMPLATE)

        # Compose the sub-agent creation input, including the copied permission rules
        creation_input = {
            "user_id": self._user_id,
            "session_id": self._session_id,
            "name": params.name,
            "description": params.description,
            "prompt": params.prompt,
            "permission_rules": permission_rules,
            "system_prompt_template": sub_agent_template.system_prompt_template,
            # Include other needed parameters from the template or params
        }

        # Assume a method or service to create agent; replace with actual implementation
        sub_agent_id = await self._create_agent(creation_input)

        return sub_agent_id

    async def _create_agent(self, creation_input: dict) -> str:
        """Placeholder method to create an agent, should integrate with actual agent creation logic.

        Args:
            creation_input (dict): Sub-agent creation parameters.

        Returns:
            str: The created sub-agent ID.
        """
        # This is a placeholder. Actual implementation should interact with agent management.
        # For now, simulate creation and return an id string.
        # Replace this with actual agent creation code.
        import uuid
        return str(uuid.uuid4())
</patched>
```