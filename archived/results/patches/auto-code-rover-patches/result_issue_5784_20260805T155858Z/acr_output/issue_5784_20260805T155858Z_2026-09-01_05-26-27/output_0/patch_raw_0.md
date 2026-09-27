The main issue is that the `AgentState` TypedDict has the fields `is_last_step` and `remaining_steps` marked as required, but they are meant to be optional as per the usage patterns. We need to mark these fields as `NotRequired` from `typing_extensions`.

Additionally, the `AgentStatePydantic` class should be updated to include the `is_last_step` field as optional with a default None, to stay consistent with the TypedDict.

Finally, the docstring and validation logic for the `state_schema` parameter `AgentState` in the `create_react_agent` function currently state that `remaining_steps` is required. This should be changed so only `messages` is required, and `remaining_steps` and `is_last_step` are optional fields.

The imports should be updated to import `NotRequired` from `typing_extensions`.

These changes ensure type correctness and consistency, aligning the code's typings and validation logic with reality.

---

# modification 1: update imports and AgentState TypedDict to mark fields as NotRequired

```
<file>libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py</file>
<original>from typing_extensions import Annotated, TypedDict
</original>
<patched>from typing_extensions import Annotated, NotRequired, TypedDict
</patched>
```

```
<file>libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py</file>
<original>class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    is_last_step: IsLastStep

    remaining_steps: RemainingSteps
</original>
<patched>class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    is_last_step: NotRequired[IsLastStep]

    remaining_steps: NotRequired[RemainingSteps]
</patched>
```

# modification 2: add optional is_last_step field to AgentStatePydantic

```
<file>libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py</file>
<original>class AgentStatePydantic(BaseModel):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    remaining_steps: RemainingSteps = 25
</original>
<patched>class AgentStatePydantic(BaseModel):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    remaining_steps: RemainingSteps = 25

    is_last_step: Optional[bool] = None
</patched>
```

# modification 3: update docstring and validation logic for state_schema keys in create_react_agent

```
<file>libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py</file>
<original>283 ) -> CompiledStateGraph:
284     """Creates an agent graph that calls tools in a loop until a stopping condition is met.
285 
286     For more details on using `create_react_agent`, visit [Agents](https://langchain-ai.github.io/langgraph/agents/overview/) documentation.
287 
288     Args:
289         model: The language model for the agent. Supports static and dynamic
290             model selection.
291 
292             - **Static model**: A chat model instance (e.g., `ChatOpenAI()`) or
293               string identifier (e.g., `"openai:gpt-4"`)
294             - **Dynamic model**: A callable with signature
295               `(state, runtime) -> BaseChatModel` that returns different models
296               based on runtime context
297               If the model has tools bound via `.bind_tools()` or other configurations,
298               the return type should be a Runnable[LanguageModelInput, BaseMessage]
299               Coroutines are also supported, allowing for asynchronous model selection.
300 
301             Dynamic functions receive graph state and runtime, enabling
302             context-dependent model selection. Must return a `BaseChatModel`
303             instance. For tool calling, bind tools using `.bind_tools()`.
304             Bound tools must be a subset of the `tools` parameter.
305 
306             Dynamic model example:
307             ```python
308             from dataclasses import dataclass
309 
310             @dataclass
311             class ModelContext:
312                 model_name: str = "gpt-3.5-turbo"
313 
314             # Instantiate models globally
315             gpt4_model = ChatOpenAI(model="gpt-4")
316             gpt35_model = ChatOpenAI(model="gpt-3.5-turbo")
317 
318             def select_model(state: AgentState, runtime: Runtime[ModelContext]) -> ChatOpenAI:
319                 model_name = runtime.context.model_name
320                 model = gpt4_model if model_name == "gpt-4" else gpt35_model
321                 return model.bind_tools(tools)
322             ```
323 
324             !!! note "Dynamic Model Requirements"
325                 Ensure returned models have appropriate tools bound via
326                 `.bind_tools()` and support required functionality. Bound tools
327                 must be a subset of those specified in the `tools` parameter.
328 
329         tools: A list of tools or a ToolNode instance.
330             If an empty list is provided, the agent will consist of a single LLM node without tool calling.
331         prompt: An optional prompt for the LLM. Can take a few different forms:
332 
333             - str: This is converted to a SystemMessage and added to the beginning of the list of messages in state["messages"].
334             - SystemMessage: this is added to the beginning of the list of messages in state["messages"].
335             - Callable: This function should take in full graph state and the output is then passed to the language model.
336             - Runnable: This runnable should take in full graph state and the output is then passed to the language model.
337 
338         response_format: An optional schema for the final agent output.
339 
340             If provided, output will be formatted to match the given schema and returned in the 'structured_response' state key.
341             If not provided, `structured_response` will not be present in the output state.
342             Can be passed in as:
343 
344                 - an OpenAI function/tool schema,
345                 - a JSON Schema,
346                 - a TypedDict class,
347                 - or a Pydantic class.
348                 - a tuple (prompt, schema), where schema is one of the above.
349                     The prompt will be used together with the model that is being used to generate the structured response.
350 
351             !!! Important
352                 `response_format` requires the model to support `.with_structured_output`
353 
354             !!! Note
355                 The graph will make a separate call to the LLM to generate the structured response after the agent loop is finished.
356                 This is not the only strategy to get structured responses, see more options in [this guide](https://langchain-ai.github.io/langgraph/how-tos/react-agent-structured-output/).
357 
358         pre_model_hook: An optional node to add before the `agent` node (i.e., the node that calls the LLM).
359             Useful for managing long message histories (e.g., message trimming, summarization, etc.).
360             Pre-model hook must be a callable or a runnable that takes in current graph state and returns a state update in the form of
361                 ```python
362                 # At least one of `messages` or `llm_input_messages` MUST be provided
363                 {
364                     # If provided, will UPDATE the `messages` in the state
365                     "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), ...],
366                     # If provided, will be used as the input to the LLM,
367                     # and will NOT UPDATE `messages` in the state
368                     "llm_input_messages": [...],
369                     # Any other state keys that need to be propagated
370                     ...
371                 }
372                 ```
373 
374             !!! Important
375                 At least one of `messages` or `llm_input_messages` MUST be provided and will be used as an input to the `agent` node.
376                 The rest of the keys will be added to the graph state.
377 
378             !!! Warning
379                 If you are returning `messages` in the pre-model hook, you should OVERWRITE the `messages` key by doing the following:
380 
381                 ```python
382                 {
383                     "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *new_messages]
384                     ...
385                 }
386                 ```
387         post_model_hook: An optional node to add after the `agent` node (i.e., the node that calls the LLM).
388             Useful for implementing human-in-the-loop, guardrails, validation, or other post-processing.
389             Post-model hook must be a callable or a runnable that takes in current graph state and returns a state update.
390 
391             !!! Note
392                 Only available with `version="v2"`.
393         state_schema: An optional state schema that defines graph state.
394             Must have `messages` and `remaining_steps` keys.
395             Defaults to `AgentState` that defines those two keys.
396         context_schema: An optional schema for runtime context.
397         checkpointer: An optional checkpoint saver object. This is used for persisting
398             the state of the graph (e.g., as chat memory) for a single thread (e.g., a single conversation).
399         store: An optional store object. This is used for persisting data
400             across multiple threads (e.g., multiple conversations / users).
401         interrupt_before: An optional list of node names to interrupt before.
402             Should be one of the following: "agent", "tools".
403             This is useful if you want to add a user confirmation or other interrupt before taking an action.
404         interrupt_after: An optional list of node names to interrupt after.
405             Should be one of the following: "agent", "tools".
406             This is useful if you want to return directly or run additional processing on an output.
407         debug: A flag indicating whether to enable debug mode.
408         version: Determines the version of the graph to create.
409             Can be one of:
410 
411             - `"v1"`: The tool node processes a single message. All tool
412                 calls in the message are executed in parallel within the tool node.
413             - `"v2"`: The tool node processes a tool call.
414                 Tool calls are distributed across multiple instances of the tool
415                 node using the [Send](https://langchain-ai.github.io/langgraph/concepts/low_level/#send)
416                 API.
417         name: An optional name for the CompiledStateGraph.
418             This name will be automatically used when adding ReAct agent graph to another graph as a subgraph node -
419             particularly useful for building multi-agent systems.
420 
421     !!! warning "`config_schema` Deprecated"
422         The `config_schema` parameter is deprecated in v0.6.0 and support will be removed in v2.0.0.
423         Please use `context_schema` instead to specify the schema for run-scoped context.
424 
425 
426     Returns:
427         A compiled LangChain runnable that can be used for chat interactions.
428 
429     The "agent" node calls the language model with the messages list (after applying the prompt).
430     If the resulting AIMessage contains `tool_calls`, the graph will then call the ["tools"][langgraph.prebuilt.tool_node.ToolNode].
431     The "tools" node executes the tools (1 tool per `tool_call`) and adds the responses to the messages list
432     as `ToolMessage` objects. The agent node then calls the language model again.
433     The process repeats until no more `tool_calls` are present in the response.
434     The agent then returns the full list of messages as a dictionary containing the key "messages".
435 
436     ``` mermaid
437         sequenceDiagram
438             participant U as User
439             participant A as LLM
440             participant T as Tools
441             U->>A: Initial input
442             Note over A: Prompt + LLM
443             loop while tool_calls present
444                 A->>T: Execute tools
445                 T-->>A: ToolMessage for each tool_calls
446             end
447             A->>U: Return final state
448     ```
449 
450     Example:
451         ```python
452         from langgraph.prebuilt import create_react_agent
453 
454         def check_weather(location: str) -> str:
455             '''Return the weather forecast for the specified location.'''
456             return f"It's always sunny in {location}"
457 
458         graph = create_react_agent(
459             "anthropic:claude-3-7-sonnet-latest",
460             tools=[check_weather],
461             prompt="You are a helpful assistant",
462         )
463         inputs = {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
464         for chunk in graph.stream(inputs, stream_mode="updates"):
465             print(chunk)
466         ```
467     """
468     if (
469         config_schema := deprecated_kwargs.pop("config_schema", MISSING)
470     ) is not MISSING:
471         warn(
472             "`config_schema` is deprecated and will be removed. Please use `context_schema` instead.",
473             category=LangGraphDeprecatedSinceV10,
474         )
475 
476         if context_schema is None:
477             context_schema = config_schema
478 
479     if version not in ("v1", "v2"):
480         raise ValueError(
481             f"Invalid version {version}. Supported versions are 'v1' and 'v2'."
482         )
483 
484     if state_schema is not None:
485         required_keys = {"messages", "remaining_steps"}
486         if response_format is not None:
487             required_keys.add("structured_response")
488 
489         schema_keys = set(get_type_hints(state_schema))
490         if missing_keys := required_keys - set(schema_keys):
491             raise ValueError(f"Missing required key(s) {missing_keys} in state_schema")
492 
493     if state_schema is None:
494         state_schema = (
495             AgentStateWithStructuredResponse
496             if response_format is not None
497             else AgentState
498         )</original>
<patched>283 ) -> CompiledStateGraph:
284     """Creates an agent graph that calls tools in a loop until a stopping condition is met.
285 
286     For more details on using `create_react_agent`, visit [Agents](https://langchain-ai.github.io/langgraph/agents/overview/) documentation.
287 
288     Args:
289         model: The language model for the agent. Supports static and dynamic
290             model selection.
291 
292             - **Static model**: A chat model instance (e.g., `ChatOpenAI()`) or
293               string identifier (e.g., `"openai:gpt-4"`)
294             - **Dynamic model**: A callable with signature
295               `(state, runtime) -> BaseChatModel` that returns different models
296               based on runtime context
297               If the model has tools bound via `.bind_tools()` or other configurations,
298               the return type should be a Runnable[LanguageModelInput, BaseMessage]
299               Coroutines are also supported, allowing for asynchronous model selection.
300 
301             Dynamic functions receive graph state and runtime, enabling
302             context-dependent model selection. Must return a `BaseChatModel`
303             instance. For tool calling, bind tools using `.bind_tools()`.
304             Bound tools must be a subset of the `tools` parameter.
305 
306             Dynamic model example:
307             ```python
308             from dataclasses import dataclass
309 
310             @dataclass
311             class ModelContext:
312                 model_name: str = "gpt-3.5-turbo"
313 
314             # Instantiate models globally
315             gpt4_model = ChatOpenAI(model="gpt-4")
316             gpt35_model = ChatOpenAI(model="gpt-3.5-turbo")
317 
318             def select_model(state: AgentState, runtime: Runtime[ModelContext]) -> ChatOpenAI:
319                 model_name = runtime.context.model_name
320                 model = gpt4_model if model_name == "gpt-4" else gpt35_model
321                 return model.bind_tools(tools)
322             ```
323 
324             !!! note "Dynamic Model Requirements"
325                 Ensure returned models have appropriate tools bound via
326                 `.bind_tools()` and support required functionality. Bound tools
327                 must be a subset of those specified in the `tools` parameter.
328 
329         tools: A list of tools or a ToolNode instance.
330             If an empty list is provided, the agent will consist of a single LLM node without tool calling.
331         prompt: An optional prompt for the LLM. Can take a few different forms:
332 
333             - str: This is converted to a SystemMessage and added to the beginning of the list of messages in state["messages"].
334             - SystemMessage: this is added to the beginning of the list of messages in state["messages"].
335             - Callable: This function should take in full graph state and the output is then passed to the language model.
336             - Runnable: This runnable should take in full graph state and the output is then passed to the language model.
337 
338         response_format: An optional schema for the final agent output.
339 
340             If provided, output will be formatted to match the given schema and returned in the 'structured_response' state key.
341             If not provided, `structured_response` will not be present in the output state.
342             Can be passed in as:
343 
344                 - an OpenAI function/tool schema,
345                 - a JSON Schema,
346                 - a TypedDict class,
347                 - or a Pydantic class.
348                 - a tuple (prompt, schema), where schema is one of the above.
349                     The prompt will be used together with the model that is being used to generate the structured response.
350 
351             !!! Important
352                 `response_format` requires the model to support `.with_structured_output`
353 
354             !!! Note
355                 The graph will make a separate call to the LLM to generate the structured response after the agent loop is finished.
356                 This is not the only strategy to get structured responses, see more options in [this guide](https://langchain-ai.github.io/langgraph/how-tos/react-agent-structured-output/).
357 
358         pre_model_hook: An optional node to add before the `agent` node (i.e., the node that calls the LLM).
359             Useful for managing long message histories (e.g., message trimming, summarization, etc.).
360             Pre-model hook must be a callable or a runnable that takes in current graph state and returns a state update in the form of
361                 ```python
362                 # At least one of `messages` or `llm_input_messages` MUST be provided
363                 {
364                     # If provided, will UPDATE the `messages` in the state