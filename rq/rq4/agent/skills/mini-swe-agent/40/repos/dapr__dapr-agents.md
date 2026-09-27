# Repo Identity
The repository dapr/dapr-agents provides Agentic Workflows Made Simple, focused on simplifying the orchestration of agent workflows. The maintainers are The Dapr Authors.

# Typical Issue Shape
- Issues generally include bug reports, enhancements, and regressions.
- Many issues contain detailed reproduction steps and expected vs actual behavior making them well-specified.
- There is no formal bug template, but users describe their challenges using agent workflows.

# Recurring Fix Patterns
- When you see issues related to workflow completion, the typical fix involves introducing an onWorkflowCompletion callback in dapr_agents/agents/orchestrators/base.py to enable automatic retrieval of workflow results. Example from issue 209:  
  ```
  # Add a callback to finalize the workflow execution
  final_summary_callback: Optional[Callable[[str], None]] = None,
  ```

- Encountering a blocking issue in workflow concurrency (as in issue 563) often requires modifying the workflow runner to remove locks. The patch includes: 
  ```
  # Remove blocking lock on workflow scheduling
  self._client_lock = threading.Lock()
  ```

- Adjusting the error handling logic to return content even on service response errors is common for issues like issue 83. The patch shows: 
  ```
  if hasattr(result, content) and result.content:
      return text_contents
  ```

# Files / Modules that Change Most Often
| Path                                   | Why it gets touched                                             |
|----------------------------------------|---------------------------------------------------------------|
| dapr_agents/agents/orchestrators/   | Frequently modified for enhancements and bug fixes regarding workflow logic. |
| dapr_agents/workflow/runners/base.py| Often touched for changes to concurrency handling in runs.      |
| dapr_agents/tool/mcp/client.py      | Regularly updated for finer error handling in tool communication. |

# Pitfalls
- Forgetting to manage callback mechanisms can lead to completed workflows not notifying users.
- Assuming all error messages require raising exceptions can hinder useful feedback from results.
- Misconfigurations in agent concurrency might result in unexpected blockages during workflow execution.

# Test Conventions
Tests reside in the tests/ directory and can be run using standard pytest command line methods. They typically follow the naming pattern test_<module_name>.py and use descriptive names reflective of their functionality.

# Worked Example
**Issue 563: Orchestrator agent only allows one active run at a time**. The fix involved removing the lock on workflow creation to allow multiple executions concurrently. For details, see the [issue link](https://github.com/dapr/dapr-agents/issues/563) and the associated [PR](https://github.com/dapr/dapr-agents/pull/564).
