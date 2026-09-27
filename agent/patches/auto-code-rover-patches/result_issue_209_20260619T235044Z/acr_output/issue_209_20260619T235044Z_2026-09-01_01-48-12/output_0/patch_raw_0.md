The goal is to add a programmatic mechanism to receive the final workflow result via a callback, rather than relying solely on logs. This involves:

1. Adding an `on_workflow_completion` callback attribute to the `DurableAgent` class to allow users to register a function that accepts the final result.

2. Modifying the `agent_workflow` method to invoke this callback passing the `final_message` once the workflow completes (after all existing processing including broadcasting, sending responses, finalizing workflow, and logging). 

3. Ensuring the callback is called only when not replaying (to avoid multiple invocations during workflow replay cycles).

4. Also adding a convenience method `run_workflow` to `DurableAgent` to run the workflow and trigger the callback automatically when done — this gives a clean programmatic entrypoint for end users.

No other existing functionality is changed, preserving compatibility.

---

# modification 1
Add `on_workflow_completion` attribute in the constructor of `DurableAgent`.

```
<file>dapr_agents/agents/durable.py</file>
<original>        self._runtime_owned = runtime is None
        self._registered = False
        self._started = False
</original>
<patched>        self._runtime_owned = runtime is None
        self._registered = False
        self._started = False

        # Callback to be invoked on workflow completion, receives final result dict
        self.on_workflow_completion: Optional[Callable[[Dict[str, Any]], Any]] = None
</patched>
```

---

# modification 2
Modify `agent_workflow` to invoke this callback (if present) after all existing processing and logging, just before returning `final_message`. This should be skipped during replay.

```
<file>dapr_agents/agents/durable.py</file>
<original>317         if not ctx.is_replaying:
318             verdict = (
319                 "max_iterations_reached"
320                 if turn == self.execution.max_iterations
321                 else "completed"
322             )
323             logger.info(
324                 "Workflow %s finalized for agent %s with verdict=%s",
325                 ctx.instance_id,
326                 self.name,
327                 verdict,
328             )
329 
330         return final_message</original>
<patched>317         if not ctx.is_replaying:
318             verdict = (
319                 "max_iterations_reached"
320                 if turn == self.execution.max_iterations
321                 else "completed"
322             )
323             logger.info(
324                 "Workflow %s finalized for agent %s with verdict=%s",
325                 ctx.instance_id,
326                 self.name,
327                 verdict,
328             )
329
330             # Call the on_workflow_completion callback if set
331             if self.on_workflow_completion:
332                 try:
333                     self.on_workflow_completion(final_message)
334                 except Exception as exc:
335                     logger.exception(
336                         "Error in on_workflow_completion callback: %s", exc
337                     )
338
339         return final_message</patched>
```

---

# modification 3
Add a helper method `run_workflow` to start and run the workflow, returning the result asynchronously and invoking the callback when complete.

```
<file>dapr_agents/agents/durable.py</file>
<original>    # ------------------------------------------------------------------
    # Runtime control
    # ------------------------------------------------------------------
    def start(
        self,
        runtime: Optional[wf.WorkflowRuntime] = None,
        *,
        auto_register: bool = True,
    ) -> None:</original>
<patched>    # ------------------------------------------------------------------
    # Runtime control
    # ------------------------------------------------------------------

    def run_workflow(self, input_message: dict) -> Dict[str, Any]:
        """
        Run the agent_workflow with the given input_message and return the final result.

        If on_workflow_completion callback is set, it will be invoked with the final result.

        Args:
            input_message: The trigger payload for the workflow.

        Returns:
            The final assistant message dict.
        """
        # Run the workflow synchronously using the runtime
        result = self.runtime.run_workflow(self.agent_workflow, input_message)

        # Invoke callback if set
        if self.on_workflow_completion:
            try:
                self.on_workflow_completion(result)
            except Exception as exc:
                logger.exception(
                    "Error in on_workflow_completion callback: %s", exc
                )

        return result

    def start(
        self,
        runtime: Optional[wf.WorkflowRuntime] = None,
        *,
        auto_register: bool = True,
    ) -> None:</patched>
```