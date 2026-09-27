## 1. Definition of an Agent Repository

An **Agent Repository** refers to a codebase that implements or contains an **LLM-based agent system**. According to the paper, an LLM-based agent system represents a new software paradigm whose operational logic is driven by a large language model (LLM), and which exhibits autonomous planning, memory management, environmental perception, and tool-use capabilities. If a repository satisfies some of the core components and features listed in Section 2, it should be considered an Agent Repository.

## 2. Core Components of an Agent Repository

### 2.1 LLM-Controlled “Brain”

* Contains task decomposition and scheduling (planning) logic.
* Maintains and retrieves historical actions or conversational records (memory).

### 2.2 Perception Component

* Receives and processes information from the environment or external inputs (e.g., user inputs, events, files, or sensors).

### 2.3 Action / Tooling Component

* Executes actions by invoking external tools or APIs (e.g., search, shell execution, database queries, third-party service calls, or custom plugins).

### 2.4 Single/Multi-Agent Architecture Support

* Supports either single-agent operation or multi-agent orchestration logic for collaboration.

### 2.5 Integration with LLM Providers

* Explicitly uses or is compatible with one or more LLM providers (via SDKs, API keys, or model configuration parameters).

### 2.6 Bonus: Runtime and Reproducibility Artifacts

* Optional but common: Docker environments, failure-triggering tests, configuration files, or example prompts/scenarios.

## 3. Distinguishing Features Compared to Traditional Software

### 3.1 Nondeterministic Behavior

System outputs depend on the LLM’s random/contextual generation, so identical inputs may yield different results.

### 3.2 Strong External Dependence and Volatility

Depends heavily on LLM providers, tool services, and external resources, which are subject to frequent changes.

### 3.3 Cross-Component Interaction Failures

Issues often span multiple components (LLM invocation, memory management, tool interfaces, workflow control) and cannot be covered by traditional unit testing.

### 3.4 Prompt and Context Management as First-Class Engineering Concerns

Prompt libraries, context length handling, and prompt update strategies directly affect system behavior.

### 3.5 Interactive or Automated Workflow Orientation

Agent workflows (including loops, task decomposition, and state checks) may cause hanging or infinite-loop behavior at runtime.

## 4. Agent Hooks

A repository is likely to be an Agent Repository if it contains the following entities or code paths:

4.1 Dependencies or invocations related to an LLM provider (e.g., `openai`, `anthropic`, or a custom provider wrapper).

4.2 Explicit `prompt`, `templates`, or `prompts` directories/resources.

4.3 Implementation of a memory component (e.g., vector database, session store, memory store, or history module).

4.4 Tool/plugin invocation code (e.g., `tools/`, `plugins/`, `tool_wrappers/`, or external API calls).

4.5 Orchestration logic or agent loop (e.g., `planner`, `scheduler`, or similar components controlling agent behavior).

4.6 LLM-related configuration (model names, token limits, API keys, context length settings).

4.7 README or examples containing terms like “agent,” “planner,” “assistant loop,” or “tool invocation.”

## 5. Quick Checklist for Repository Classification

> Based on the paper, the following checklist can be used to quickly assess whether a repository qualifies as an Agent Repository:

* Does the README or code explicitly mention “agent,” “planner,” “tool invocation,” “memory,” or “LLM”? (Yes → likely Agent)

* Does the code call or depend on an LLM provider’s SDK? (Yes → likely Agent)

* Does the repository include a `prompt/`, `templates/`, or `prompts/` directory, or code managing prompts? (Yes → likely Agent)

* Does it implement memory storage (e.g., vector DB, session store, memory module)? (Yes → likely Agent)

* Does it include wrappers or calls to external tools/plugins? (Yes → likely Agent)

* Does it contain orchestration or an agent loop (planner/scheduler)? (Yes → strongly Agent)

If three or more items are satisfied, the repository is **likely** an Agent Repository; if five or more are satisfied, it is **highly likely**.

