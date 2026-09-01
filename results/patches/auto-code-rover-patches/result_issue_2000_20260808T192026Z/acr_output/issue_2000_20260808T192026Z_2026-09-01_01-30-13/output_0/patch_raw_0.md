```
<file>src/agentscope/agent/_agent.py</file>
<original>1635         # ===================================================================
1636         # Step 2: Check permission by toolkit and permission engine
1637         # ===================================================================
1638         if tool_call.state == ToolCallState.ALLOWED:
1639             # Already allowed by user confirmation, skip permission checking
1640             decision = PermissionDecision(
1641                 behavior=PermissionBehavior.ALLOW,
1642                 message="Already allowed by user confirmation.",
1643             )
1644         else:
1645             decision = await self._engine.check_permission(
1646                 tool,
1647                 parsed_input,
1648             )
</original>
<patched>1635         # ===================================================================
1636         # Step 2: Check permission by middleware chain around permission engine
1637         # ===================================================================
1638         if tool_call.state == ToolCallState.ALLOWED:
1639             # Already allowed by user confirmation, skip permission checking
1640             decision = PermissionDecision(
1641                 behavior=PermissionBehavior.ALLOW,
1642                 message="Already allowed by user confirmation.",
1643             )
1644         else:
1645             # Prepare input_kwargs for middleware
1646             input_kwargs = {
1647                 "tool_call": tool_call,
1648                 "tool": tool,
1649                 "tool_input": parsed_input,
1650             }
1651 
1652             # Compose the middleware chain for on_check_permission if any
1653             if not self._permission_check_middlewares:
1654                 decision = await self._engine.check_permission(
1655                     tool,
1656                     parsed_input,
1657                 )
1658             else:
1659                 async def execute_chain(index: int = 0) -> PermissionDecision:
1660                     if index >= len(self._permission_check_middlewares):
1661                         # Innermost handler - call the permission engine
1662                         return await self._engine.check_permission(
1663                             tool,
1664                             parsed_input,
1665                         )
1666                     else:
1667                         mw = self._permission_check_middlewares[index]
1668 
1669                         async def next_handler(**kwargs: dict) -> PermissionDecision:
1670                             return await execute_chain(index + 1)
1671 
1672                         return await mw.on_check_permission(
1673                             agent=self,
1674                             input_kwargs=input_kwargs,
1675                             next_handler=next_handler,
1676                         )
1677 
1678                 decision = await execute_chain()
</patched>
</file>

<file>src/agentscope/agent/_agent.py</file>
<original>174    def __init__(
175        self,
176        name: str,
177        system_prompt: str,
178        model: ChatModelBase,
179        toolkit: Toolkit | None = None,
180        middlewares: list[MiddlewareBase] | None = None,
181        state: AgentState | None = None,
182        offloader: Offloader | None = None,
183        # The agent configurations
184        model_config: ModelConfig | None = None,
185        context_config: ContextConfig | None = None,
186        react_config: ReActConfig | None = None,
187    ) -> None:
188        """Initialize the agent class in AgentScope.
189 
190        Args:
191            name (`str`):
192                The agent identifier.
193            system_prompt (`str`):
194                The agent's system prompt. Additional instructions may be
195                appended to it dynamically during operation.
196            model (`ChatModelBase`):
197                The chat model/llm used for this agent.
198            toolkit (`Toolkit | None`, optional):
199                The toolkit used for registering tools, MCPs and skills as the
200                sole source.
201            middlewares (`list[MiddlewareBase] | None`, optional):
202                Middlewares applied to the agent to modify its behavior
203                without altering its source code. Supported hook points
204                include: reply, reasoning, acting, model call, and system
205                prompt retrieval.
206            state (`AgentState | None`, optional):
207                The agent state. A new state will be created if not provided.
208            offloader (`Offloader | None`, optional):
209                The context offloader. If provided, the compressed context and
210                tool result will be offloaded.
211            model_config (`ModelConfig | None`, optional):
212                The additional chat model configuration including fallback
213                model and retries.
214            context_config (`ContextConfig | None`, optional):
215                The context config for context compression and tool result
216                compression.
217            react_config (`ReActConfig | None`, optional):
218                The config for the reasoning-acting loop.
219        """
220        self.name = name
221        self._system_prompt = system_prompt
222        self.model = model
223        self.state = state or AgentState()
224 
225        self.model_config = model_config or ModelConfig()
226        self.context_config = context_config or ContextConfig()
227        self.react_config = react_config or ReActConfig()
228 
229        # The permission engine
230        self._engine = PermissionEngine(self.state.permission_context)
231 
232        # The offloader/workspace
233        self.offloader = offloader
234 
235        # ====================================================================
236        # The Tool-related logics
237        # ====================================================================
238        self.toolkit = toolkit or Toolkit()
239 
240        # ====================================================================
241        # The Middleware-related attributes
242        # ====================================================================
243        # Filter middlewares by implemented hooks (only once)
244        middlewares = middlewares or []
245        self._reply_middlewares = [
246            _ for _ in middlewares if _.is_implemented("on_reply")
247        ]
248        self._reasoning_middlewares = [
249            _ for _ in middlewares if _.is_implemented("on_reasoning")
250        ]
251        self._acting_middlewares = [
252            _ for _ in middlewares if _.is_implemented("on_acting")
253        ]
254        self._model_call_middlewares = [
255            _ for _ in middlewares if _.is_implemented("on_model_call")
256        ]
257        self._system_prompt_middlewares = [
258            _ for _ in middlewares if _.is_implemented("on_system_prompt")
259        ]
260        self._compress_context_middlewares = [
261            _ for _ in middlewares if _.is_implemented("on_compress_context")
262        ]
</original>
<patched>174    def __init__(
175        self,
176        name: str,
177        system_prompt: str,
178        model: ChatModelBase,
179        toolkit: Toolkit | None = None,
180        middlewares: list[MiddlewareBase] | None = None,
181        state: AgentState | None = None,
182        offloader: Offloader | None = None,
183        # The agent configurations
184        model_config: ModelConfig | None = None,
185        context_config: ContextConfig | None = None,
186        react_config: ReActConfig | None = None,
187    ) -> None:
188        """Initialize the agent class in AgentScope.
189 
190        Args:
191            name (`str`):
192                The agent identifier.
193            system_prompt (`str`):
194                The agent's system prompt. Additional instructions may be
195                appended to it dynamically during operation.
196            model (`ChatModelBase`):
197                The chat model/llm used for this agent.
198            toolkit (`Toolkit | None`, optional):
199                The toolkit used for registering tools, MCPs and skills as the
200                sole source.
201            middlewares (`list[MiddlewareBase] | None`, optional):
202                Middlewares applied to the agent to modify its behavior
203                without altering its source code. Supported hook points
204                include: reply, reasoning, acting, model call, permission
205                checking, and system prompt retrieval.
206            state (`AgentState | None`, optional):
207                The agent state. A new state will be created if not provided.
208            offloader (`Offloader | None`, optional):
209                The context offloader. If provided, the compressed context and
210                tool result will be offloaded.
211            model_config (`ModelConfig | None`, optional):
212                The additional chat model configuration including fallback
213                model and retries.
214            context_config (`ContextConfig | None`, optional):
215                The context config for context compression and tool result
216                compression.
217            react_config (`ReActConfig | None`, optional):
218                The config for the reasoning-acting loop.
219        """
220        self.name = name
221        self._system_prompt = system_prompt
222        self.model = model
223        self.state = state or AgentState()
224 
225        self.model_config = model_config or ModelConfig()
226        self.context_config = context_config or ContextConfig()
227        self.react_config = react_config or ReActConfig()
228 
229        # The permission engine
230        self._engine = PermissionEngine(self.state.permission_context)
231 
232        # The offloader/workspace
233        self.offloader = offloader
234 
235        # ====================================================================
236        # The Tool-related logics
237        # ====================================================================
238        self.toolkit = toolkit or Toolkit()
239 
240        # ====================================================================
241        # The Middleware-related attributes
242        # ====================================================================
243        # Filter middlewares by implemented hooks (only once)
244        middlewares = middlewares or []
245        self._reply_middlewares = [
246            _ for _ in middlewares if _.is_implemented("on_reply")
247        ]
248        self._reasoning_middlewares = [
249            _ for _ in middlewares if _.is_implemented("on_reasoning")
250        ]
251        self._acting_middlewares = [
252            _ for _ in middlewares if _.is_implemented("on_acting")
253        ]
254        self._permission_check_middlewares = [
255            _ for _ in middlewares if _.is_implemented("on_check_permission")
256        ]
257        self._model_call_middlewares = [
258            _ for _ in middlewares if _.is_implemented("on_model_call")
259        ]
260        self._system_prompt_middlewares = [
261            _ for _ in middlewares if _.is_implemented("on_system_prompt")
262        ]
263        self._compress_context_middlewares = [
264            _ for _ in middlewares if _.is_implemented("on_compress_context")
265        ]
</patched>
</file>

<file>src/agentscope/middleware/_base.py</file>
<original>65     async def on_reply(
66         self,
67         agent: "Agent",
68         input_kwargs: dict,
69         next_handler: Callable[..., AsyncGenerator],
70     ) -> AsyncGenerator:
71         """Hook for intercepting the reply process.
72 
73         Args:
74             agent: The Agent instance executing this middleware
75             input_kwargs: Dictionary containing:
76                 - inputs: Msg | list[Msg] | UserConfirmResultEvent |
77                 ExternalExecutionResultEvent | None — the unified inputs
78                 that trigger this reply (new message(s), a resumption
79                 event from a previous outside interaction, or None).
80             next_handler: Callable that executes the next middleware or
81              original method
82 
83         Yields:
84             AgentEvent | Msg: Events from the reply process
85         """
86         raise RuntimeError(
87             f"{type(self).__name__} does not implement on_reply",
88         )
89         yield  # pylint: disable=unreachable
90 
91     async def on_reasoning(
92         self,
93         agent: "Agent",
94         input_kwargs: dict,
95         next_handler: Callable[..., AsyncGenerator],
96     ) -> AsyncGenerator:
97         """Hook for intercepting the reasoning process.
98 
99         Args:
100             agent: The Agent instance executing this middleware
101             input_kwargs: Dictionary containing:
102                 - tool_choice: ToolChoice (default None)
103             next_handler: Callable that executes the next middleware or
104             original method
105 
106         Yields:
107             Various events from the reasoning process
108         """
109         raise RuntimeError(
110             f"{type(self).__name__} does not implement on_reasoning",
111         )
112         yield  # pylint: disable=unreachable
113 
114     async def on_acting(
115         self,
116         agent: "Agent",
117         input_kwargs: dict,
118         next_handler: Callable[..., AsyncGenerator],
119     ) -> AsyncGenerator:
120         """Hook for intercepting the raw tool execution.
121 
122         This hook wraps **only** the ``toolkit.call_tool`` call — i.e. the
123         pure I/O execution layer.  Permission checking, input validation, and
124         context writes are handled by the agent **outside** this hook and are
</original>
<patched>65     async def on_reply(
66         self,
67         agent: "Agent",
68         input_kwargs: dict,
69         next_handler: Callable[..., AsyncGenerator],
70     ) -> AsyncGenerator:
71         """Hook for intercepting the reply process.
72 
73         Args:
74             agent: The Agent instance executing this middleware
75             input_kwargs: Dictionary containing:
76                 - inputs: Msg | list[Msg] | UserConfirmResultEvent |
77                 ExternalExecutionResultEvent | None — the unified inputs
78                 that trigger this reply (new message(s), a resumption
79                 event from a previous outside interaction, or None).
80             next_handler: Callable that executes the next middleware or
81              original method
82 
83         Yields:
84             AgentEvent | Msg: Events from the reply process
85         """
86         raise RuntimeError(
87             f"{type(self).__name__} does not implement on_reply",
88         )
89         yield  # pylint: disable=unreachable
90 
91     async def on_reasoning(
92         self,
93         agent: "Agent",
94         input_kwargs: dict,
95         next_handler: Callable[..., AsyncGenerator],
96     ) -> AsyncGenerator:
97         """Hook for intercepting the reasoning process.
98 
99         Args:
100             agent: The Agent instance executing this middleware
101             input_kwargs: Dictionary containing:
102                 - tool_choice: ToolChoice (default None)
103             next_handler: Callable that executes the next middleware or
104             original method
105 
106         Yields:
107             Various events from the reasoning process
108         """
109         raise RuntimeError(
110             f"{type(self).__name__} does not implement on_reasoning",
111         )
112         yield  # pylint: disable=unreachable
113 
114     async def on_acting(
115         self,
116         agent: "Agent",
117         input_kwargs: dict,
118         next_handler: Callable[..., AsyncGenerator],
119     ) -> AsyncGenerator:
120         """Hook for intercepting the raw tool execution.
121 
122         This hook wraps **only** the ``toolkit.call_tool`` call — i.e. the
123         pure I/O execution layer.  Permission checking, input validation, and
124         context writes are handled by the agent **outside** this hook and are
</patched>
</file>

<file>src/agentscope/middleware/_base.py</file>
<original>113 
114     async def on_acting(
115         self,
116         agent: "Agent",
117         input_kwargs: dict,
118         next_handler: Callable[..., AsyncGenerator],
119     ) -> AsyncGenerator:
120         """Hook for intercepting the raw tool execution.
121 
122         This hook wraps **only** the ``toolkit.call_tool`` call — i.e. the
123         pure I/O execution layer.  Permission checking, input validation, and
124         context writes are handled by the agent **outside** this hook and are
125         separate concerns.
126 
127         Args:
128             agent: The Agent instance executing this middleware
129             input_kwargs: Dictionary containing:
130                 - tool_call: ToolCallBlock — the resolved tool call block,
131                   with input validated and parsed by the
132                   :class:`~agentscope.tool.Toolkit`
133             next_handler: Callable that executes the next middleware or
134             original method
135 
136         Yields:
137             ToolChunk | ToolResponse: Stream of tool execution chunks
138         """
139         raise RuntimeError(
140             f"{type(self).__name__} does not implement on_acting",
141         )
142         yield  # pylint: disable=unreachable
143
</original>
<patched>113 
114     async def on_acting(
115         self,
116         agent: "Agent",
117         input_kwargs: dict,
118         next_handler: Callable[..., AsyncGenerator],
119     ) -> AsyncGenerator:
120         """Hook for intercepting the raw tool execution.
121 
122         This hook wraps **only** the ``toolkit.call_tool`` call — i.e. the
123         pure I/O execution layer.  Permission checking, input validation, and
124         context writes are handled by the agent **outside** this hook and are
125         separate concerns.
126 
127         Args:
128             agent: The Agent instance executing this middleware
129             input_kwargs: Dictionary containing:
130                 - tool_call: ToolCallBlock — the resolved tool call block,
131                   with input validated and parsed by the
132                   :class:`~agentscope.tool.Toolkit`
133             next_handler: Callable that executes the next middleware or
134             original method
135 
136         Yields:
137             ToolChunk | ToolResponse: Stream of tool execution chunks
138         """
139         raise RuntimeError(
140             f"{type(self).__name__} does not implement on_acting",
141         )
142         yield  # pylint: disable=unreachable
143 
144     async def on_check_permission(
145         self,
146         agent: "Agent",
147         input_kwargs: dict,
148         next_handler: Callable[..., Awaitable["PermissionDecision"]],
149     ) -> "PermissionDecision":
150         """Hook for intercepting the permission checking process.
151 
152         Args:
153             agent: The Agent instance executing this middleware
154             input_kwargs: Dictionary containing:
155                 - tool_call: ToolCallBlock — the resolved tool call block
156                 - tool: ToolBase — the resolved tool instance
157                 - tool_input: the validated and parsed tool input
158             next_handler: Callable that executes the next middleware or original method
159 
160         Returns:
161             PermissionDecision: The permission decision result
162         """
163         raise RuntimeError(
164             f"{type(self).__name__} does not implement on_check_permission",
165         )
166
167 </patched>
</file>
```