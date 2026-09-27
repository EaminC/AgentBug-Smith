### Repo Identity

- Repository Name: dapr/dapr-agents
- Description: Dapr Agents is a developer framework designed to build production-grade resilient AI agent systems that operate at scale.
- URL: https://github.com/dapr/dapr-agents

### Typical Issue Shape

- Issue Title: "workflow completion callback capabilities on DurableAgent"
- Description: Users reported that the workflows running on DurableAgent terminate the entire app upon calling certain methods, like os.Exit(). This raises concerns about handling results programmatically after workflow completion.

### Recurring Fix Patterns

- **Callback Enhancement:** Introduced an onWorkflowCompletion callback to handle workflow results programmatically instead of relying solely on logs.
- **Error Handling:** Improved the activity logic to prevent methods like os.Exit() from terminating the app and allow workflows to resume.

### Files / Modules That Change Most Often

- dapr_agents/agents/orchestrators/base.py
- dapr_agents/agents/orchestrators/random.py
- dapr_agents/agents/orchestrators/llm/orchestrator.py

These files often contain logic related to workflow processing and orchestration, which directly impacts the agent's performance and functionality.

### Pitfalls

- **Relying on Logs:** Users often relied solely on logs for workflow completion details. This is inefficient; implementing callback mechanisms is advisable.
- **Termination Issues:** Calling terminating methods (e.g., os.Exit) within workflows can hinder proper execution and recovery.

### Test Conventions

- **Unit Tests:** Focused on ensuring individual components operate correctly, particularly around orchestrators that handle multiple workflows.
- **Integration Tests:** Verify that agents operate seamlessly across their communication and workflow execution tasks.
- **End-to-End Tests:** To validate that entire workflows complete successfully, covering all components from initiation to final result retrieval.

### One Concrete Worked Example

- **Issue Title:** "workflow completion callback capabilities on DurableAgent"
- **Description:** The enhancement discusses adding a callback mechanism to handle results post-workflow completion, enhancing the user experience and improving application logic response to workflow outcomes.
- **Pull Request:** [Add callback method to orchestrator to get final output](https://github.com/dapr/dapr-agents/pull/279)

