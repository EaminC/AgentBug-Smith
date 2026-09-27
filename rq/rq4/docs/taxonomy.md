## 1. Definition of an Agent Issue

An **agent issue** refers to a user-reported problem (e.g., a bug report, feature request, maintenance issue, or reliability problem) that occurs in an LLM-based agent system and is related to components, behaviors, or engineering infrastructure that are **specific or particularly important to the operation of agents**.

An agent issue may concern not only the LLM itself, but also the surrounding **agent harness** that enables an agent to perceive context, invoke tools, execute actions, maintain state, coordinate workflows, operate in controlled environments, and be evaluated or monitored.

Therefore, an issue should be considered an agent issue when its resolution requires modifying or configuring one or more of the following agent-specific capabilities:

1. **LLM/provider integration**
2. **Tool interfaces and tool execution**
3. **Context and memory management**
4. **Agent lifecycle and workflow orchestration**
5. **Execution environments and sandboxes**
6. **Observability, reliability, and cost management**
7. **Verification, evaluation, and failure attribution**
8. **Agent governance, permissions, or security**

However, infrastructure or utility problems that are completely independent of agent behavior should **not** be classified as agent issues. For example, a generic Docker bug, a generic logging bug, or a generic file-handling bug is not an agent issue unless it directly affects an agent-specific capability or execution process.

---

# 2. Taxonomy of Agent Issues

We retain the original six major categories and extend their definitions using concepts from **Agent Harness Engineering**.

The taxonomy contains **6 major categories** and multiple fine-grained subcategories. The Harness Engineering dimensions should be used as **additional classification signals**, rather than replacing the original taxonomy.

---

## A. Incompatibility with LLM Providers

Issues caused by incompatibilities between the agent system and external LLM providers, provider SDKs, APIs, or supported models.

### A.1 Incompatible Dependencies

Missing, incompatible, deprecated, or improperly installed third-party libraries required to interact with LLM providers.

Examples include:

- incompatible `openai`, `anthropic`, `litellm`, or equivalent SDK versions;
- missing provider packages;
- breaking SDK changes;
- incompatible provider API versions.

### A.2 Unsupported Models

Problems where the agent cannot support or correctly operate with a particular LLM model.

Examples include:

- newly released models;
- models with different API schemas;
- models with different tool-calling behavior;
- models requiring different message formats;
- models with different multimodal capabilities.

### A.3 Incompatible Parameters to LLM Providers

Problems caused by passing unsupported, malformed, missing, or incorrectly interpreted parameters to an LLM provider.

Examples include:

- unsupported generation parameters;
- incorrect tool-calling parameters;
- incompatible structured-output parameters;
- incorrect provider-specific options;
- missing required API parameters.

---

# B. Tool-Related Issues

Issues concerning how agents **discover, select, describe, invoke, integrate, scale, or execute tools**.

This category incorporates the **Tool Interface & Protocol** dimension from Agent Harness Engineering.

### B.1 Tool Dependency Issues

Failures caused by missing, incompatible, or misconfigured dependencies required by tools.

This includes dependencies that prevent:

- tool registration;
- tool parsing;
- tool invocation;
- tool execution;
- tool result processing.

### B.2 Tool Configuration Issues

Problems caused by incorrect configuration of tools or tool-related components.

Examples include:

- incorrect retriever configuration;
- incorrect embedder configuration;
- wrong retrieval mode;
- incorrect tool routing;
- incorrect tool registration;
- incorrect tool availability configuration.

### B.3 Tool Implementation Errors

Bugs in the implementation of tools or tool-supporting components.

Examples include:

- incorrect RAG logic;
- incorrect file-processing logic;
- failures on empty tool outputs;
- token-limit handling bugs;
- incorrect argument processing;
- incorrect tool-result processing.

### B.4 Misuse of Tool Interfaces

Errors that prevent tools from being invoked or used correctly.

Examples include:

- missing or malformed parameters;
- incorrect argument types;
- serialization/deserialization failures;
- incorrect schema binding;
- incorrect tool-to-LLM binding;
- incorrect function-calling interfaces.

### B.5 Tool Description, Discovery, and Selection Issues

Issues involving how an agent understands or selects available tools.

Examples include:

- incorrect tool descriptions;
- tools not being exposed to the agent;
- incorrect tool metadata;
- tool discovery failures;
- inappropriate tool selection;
- tool-selection ambiguity;
- incorrect tool schemas causing the model to select or invoke the wrong tool.

### B.6 Tool Protocol and Interface Standard Issues

Issues caused by protocol or interface mismatches between agents and tools.

Examples include:

- MCP or equivalent protocol integration;
- incompatible tool schemas;
- protocol-version mismatches;
- incorrect request/response formats;
- incompatibility between tool servers and agent clients.

### B.7 Tool Scalability and Session Management

Issues involving tool execution across long-running or concurrent agent sessions.

Examples include:

- tool state leaking across sessions;
- concurrent tool-call failures;
- session-specific tool configuration;
- tool-server lifecycle problems;
- failures when multiple agents access the same tool infrastructure.

---

# C. Memory and Context-Related Issues

Issues concerning the information available to an agent during and across executions.

This category incorporates **Context & Memory Management** from Agent Harness Engineering.

### C.1 Memory Initialization Issues

Failures in initializing, resetting, or reconstructing agent memory.

Examples include:

- database initialization;
- workspace initialization;
- memory reset failures;
- uploaded files not being correctly associated with a new workspace;
- inconsistent initial memory states.

### C.2 Memory Content Errors

Incorrect, incomplete, duplicated, corrupted, or inconsistent information stored in memory.

Examples include:

- incorrect message attributes;
- redundant memories;
- corrupted task state;
- incorrect storage of intermediate results;
- failures caused by unsupported data types;
- serialization/deserialization errors.

### C.3 Memory Dependency Issues

Failures caused by dependencies required by memory systems.

### C.4 Short-Term Context Issues

Issues involving the active context window used during a single agent execution.

Examples include:

- incorrect context construction;
- missing messages;
- incorrect message ordering;
- failure to include relevant tool results;
- incorrect truncation of recent context.

### C.5 Session State and Cross-Run Persistence Issues

Issues involving state that persists across agent runs or sessions.

Examples include:

- state not being preserved;
- stale state being reused;
- cross-run contamination;
- incorrect workspace/session restoration.

### C.6 Long-Term Persistent Memory Issues

Issues involving persistent memory systems intended to retain information across tasks or sessions.

Examples include:

- incorrect memory retrieval;
- incorrect memory writing;
- stale persistent memories;
- failure to update long-term memory.

### C.7 Long-Horizon Context Issues

Issues involving maintaining useful context across long-running tasks.

Examples include:

- loss of important information during long tasks;
- ineffective context compression;
- incorrect summarization;
- failure to preserve important intermediate state.

### C.8 Context Drift and Context-Length Issues

Issues caused by context degradation or exceeding context limits.

Examples include:

- context-window overflow;
- incorrect token counting;
- incorrect context-length calculation;
- progressive context drift;
- irrelevant information accumulating in context.

---

# D. LLM Operation Issues

Issues concerning the operation, management, and interpretation of LLM inference within the agent.

### D.1 Model Access Misconfiguration

Examples include:

- incorrect model binding;
- missing API keys;
- incorrect authentication;
- incorrect endpoint configuration.

### D.2 Token Usage Misconfiguration

Examples include:

- incorrect maximum token limits;
- incorrect token pricing;
- incorrect token counting;
- failures in token management.

### D.3 Incorrect Model Output Handlers

Problems in parsing or processing model outputs.

Examples include:

- malformed outputs;
- empty responses;
- unexpected response structures;
- refusal handling;
- invalid structured outputs;
- unexpected tool-call outputs.

### D.4 Model Dependency Issues

Issues caused by dependencies required for model operation.

Examples include:

- tokenizers;
- provider interfaces;
- model adapters;
- model-specific libraries.

### D.5 Context Length Issues

Failures caused by exceeding or incorrectly calculating the model's context length.

### D.6 Prompt-Related Issues

Problems involving prompts or prompt management.

Examples include:

- incorrect system prompts;
- incorrect prompt templates;
- prompts not being updated;
- incorrect variable substitution;
- prompt versioning problems;
- prompt construction errors.

---

# E. Workflow, Lifecycle, and Orchestration Issues

Issues involving the **execution lifecycle, control flow, coordination, and orchestration** of agents.

This category incorporates the **Lifecycle & Orchestration** dimension from Agent Harness Engineering.

### E.1 Single-Agent Inner Loop Issues

Problems occurring inside the iterative agent loop.

Examples include:

- incorrect think-act-observe cycles;
- premature termination;
- repeated actions;
- failure to transition between reasoning and execution;
- incorrect stopping conditions.

### E.2 Multi-Agent Orchestration Issues

Problems involving coordination among multiple agents.

Examples include:

- incorrect agent handoffs;
- communication failures;
- incorrect role assignment;
- deadlocks;
- synchronization problems;
- incorrect delegation.

### E.3 Full Lifecycle Pipeline Issues

Problems spanning multiple stages of an agent task.

Examples include:

- initialization → execution → verification → termination failures;
- skipped lifecycle stages;
- incorrect cleanup;
- incorrect state transitions.

### E.4 Scheduling and Execution Issues

Problems involving task scheduling or execution.

Examples include:

- hanging;
- infinite loops;
- skipped steps;
- race conditions;
- incorrect retries;
- premature termination;
- repeated execution.

### E.5 Lifecycle Hook Issues

Problems involving callbacks or lifecycle hooks that execute before, during, or after agent execution.

Examples include:

- incorrect pre-execution hooks;
- incorrect post-execution hooks;
- cleanup hooks not firing;
- state not being persisted during lifecycle transitions.

---

# F. Utility and Agent Infrastructure Issues

This category covers supporting infrastructure. An issue should only be classified here as an **agent issue** when the utility directly supports an agent-specific capability.

---

## F.1 Execution Environment & Sandbox Issues

Issues involving the environment in which an agent executes actions.

### F.1.1 General-Purpose Managed Sandboxes

Examples:

- sandbox initialization;
- environment reset;
- resource isolation;
- execution failures specific to agent tasks.

### F.1.2 Computer-Use Agent Infrastructure

Issues involving environments where agents interact with computers through GUI, keyboard, mouse, or operating-system interfaces.

### F.1.3 Code-Specialized Sandboxes

Issues involving execution environments specifically designed for coding agents.

Examples:

- repository workspace isolation;
- code execution environments;
- test execution sandboxes.

### F.1.4 Framework-Integrated Runtimes

Issues involving runtimes tightly integrated with an agent framework.

### F.1.5 Browser Evaluation Environments

Issues involving browser-based agent execution environments.

Examples:

- browser state management;
- page interaction infrastructure;
- browser session failures.

### F.1.6 OS-Level Permission Sandboxes

Issues involving permissions required by agents to access files, processes, devices, or system resources.

### F.1.7 Sandbox Abstraction Layers

Issues involving abstraction layers that provide agents with a unified interface to different execution environments.

---

## F.2 Observability & Operations Issues

Issues concerning monitoring, tracing, cost management, and operational reliability of agents.

### F.2.1 Tracing and Monitoring

Examples:

- missing agent traces;
- incorrect trace propagation;
- incorrect recording of tool calls;
- missing intermediate agent states.

### F.2.2 Agent-Specific Operations

Examples:

- agent runtime management;
- agent deployment;
- agent health monitoring;
- agent failure recovery.

### F.2.3 Cost Tracking and Optimization

Examples:

- incorrect token cost calculation;
- incorrect per-agent cost attribution;
- failures in cost monitoring;
- inefficient retry or inference behavior that is explicitly related to agent operation.

### F.2.4 Reliability Engineering

Examples:

- agent retry mechanisms;
- failure recovery;
- fault tolerance;
- timeout handling;
- graceful degradation.

### F.2.5 Unified Observability

Issues involving the integration of traces, logs, metrics, tool calls, model calls, and agent states into a unified observability system.

---

## F.3 Verification & Evaluation Issues

Issues involving verification, evaluation, and attribution of agent behavior.

### F.3.1 Task and Benchmark Grounding

Issues involving the connection between agent execution and evaluation tasks or benchmarks.

### F.3.2 Pre-Execution Readiness Validation

Issues involving checks that should occur before an agent starts execution.

Examples include:

- missing tools;
- invalid environment;
- missing credentials;
- unavailable models;
- invalid workspace state.

### F.3.3 Controlled Execution and Trace Capture

Issues involving controlled execution and collection of execution traces.

Examples include:

- incomplete traces;
- incorrect trace capture;
- inability to reproduce an agent trajectory;
- incorrect execution isolation.

### F.3.4 Multi-Level Judgement and Failure Attribution

Issues involving determining whether and why an agent failed.

Examples include:

- incorrect success criteria;
- incorrect failure attribution;
- inability to distinguish tool failure from model failure;
- incorrect evaluator behavior.

### F.3.5 Continuous Regression and Deployment Feedback

Issues involving regression testing and feedback from deployed agents.

Examples include:

- previously solved tasks becoming broken;
- agent behavior regressions;
- missing regression tests;
- evaluation feedback not reaching the agent development pipeline.

---

## F.4 Governance & Security Issues

Issues involving permissions, identity, lifecycle control, hardening, auditing, and agent-specific security.

### F.4.1 Permission Models and Identity Management

Examples:

- incorrect agent permissions;
- incorrect identity propagation;
- unauthorized tool access;
- incorrect user/agent identity mapping.

### F.4.2 Lifecycle Hooks for Governance

Issues involving security or governance checks attached to the agent lifecycle.

Examples:

- authorization checks not being triggered;
- missing pre-execution validation;
- incorrect post-execution auditing.

### F.4.3 Component Hardening

Issues involving hardening of agent components against misuse or unintended behavior.

Examples:

- unsafe tool exposure;
- insecure agent configurations;
- insufficient isolation.

### F.4.4 Declarative Constitutions / Policies

Issues involving explicit rules or policies governing agent behavior.

Examples:

- policies not being enforced;
- incorrect policy interpretation;
- conflicting agent constraints.

### F.4.5 Audit Infrastructure

Issues involving audit trails for agent actions.

Examples:

- missing action logs;
- incomplete audit records;
- inability to trace which agent performed an action.

### F.4.6 Agent Security

Issues involving security threats specific to agent systems.

Examples include:

- prompt injection defenses;
- tool-use authorization;
- malicious tool inputs;
- agent privilege escalation;
- unsafe autonomous actions.

---

## 3. Important Classification Principle

The taxonomy should classify an issue according to the **primary agent-specific capability being affected**, rather than merely the software component mentioned in the issue.

For example:

- A Docker dependency failure is **not automatically an agent issue**.
- A Docker dependency failure that prevents a coding agent from executing generated code **is an agent issue** under **F.1 Execution Environment & Sandbox**.
- A generic database failure is **not automatically a memory issue**.
- A database failure that corrupts persistent agent memory **is a memory issue** under **C.2 Memory Content Errors**.
- A generic API parameter bug is **not automatically an agent issue**.
- An incorrect parameter passed to an LLM provider during agent inference **is an agent issue** under **A.3**.
- A generic logging bug is **not automatically an agent issue**.
- A tracing failure that prevents recording agent trajectories or tool calls **is an agent issue** under **F.2.1/F.3.3**.

The key question is:

> **Does the problem affect an agent-specific capability, execution process, or agent harness component?**

If yes, it may qualify as an agent issue.

---

# 4. Inclusion Criteria

An issue is likely an agent issue if one or more of the following signals are present:

### LLM-related signals

- LLM provider or model names;
- provider SDKs;
- API keys or authentication;
- model invocation;
- token limits;
- prompt templates;
- model output parsing;
- structured outputs.

### Tool-related signals

- tool invocation;
- function calling;
- tool schemas;
- tool descriptions;
- tool discovery;
- tool selection;
- MCP or equivalent protocols;
- RAG;
- retrievers;
- tool servers;
- tool execution.

### Context and memory signals

- conversation history;
- context windows;
- session state;
- persistent memory;
- long-term memory;
- workspace state;
- context compression;
- context drift;
- memory retrieval/storage.

### Lifecycle and orchestration signals

- agent loops;
- task scheduling;
- retries;
- delegation;
- multi-agent coordination;
- agent handoffs;
- lifecycle hooks;
- workflow execution;
- termination conditions.

### Execution environment signals

- agent sandbox;
- coding environment;
- browser environment;
- computer-use environment;
- workspace isolation;
- OS permissions;
- controlled code execution.

### Observability and evaluation signals

- agent traces;
- trajectory recording;
- tool-call tracing;
- agent-specific metrics;
- cost attribution;
- agent evaluation;
- benchmark execution;
- failure attribution;
- regression testing.

### Governance and security signals

- agent permissions;
- identity management;
- tool authorization;
- prompt injection;
- agent policy;
- auditing;
- autonomous-action restrictions.

---

# 5. Exclusion Criteria

Do **not** classify an issue as an agent issue merely because it occurs in a repository that contains an agent.

Exclude issues that are entirely independent of agent-specific behavior, including:

- generic UI bugs;
- generic Docker bugs;
- generic dependency upgrades;
- generic CI failures;
- generic database bugs;
- generic file handling;
- generic networking problems;
- generic logging problems;
- generic test failures;
- generic build failures;
- generic refactoring;
- generic documentation issues.

However, these issues become agent issues when there is clear evidence that they affect an **agent-specific capability or agent execution path**.

For example:

> "Docker image fails to build because package X is missing."

→ **Not necessarily an agent issue.**

> "The coding agent sandbox cannot execute repository tests because package X is missing from the managed execution environment."

→ **Agent issue: F.1.3 Code-Specialized Sandboxes.**

---

# 6. Evidence and Confidence Rules

Use the following evidence hierarchy when determining whether an issue is an agent issue:

### Strong evidence

1. The issue explicitly describes an agent-specific failure.
2. The affected code is clearly part of an agent's LLM/tool/memory/workflow/harness execution path.
3. The developer's patch modifies agent-specific components.
4. The issue can only occur because the software operates as an agent.

### Moderate evidence

5. The issue occurs during agent execution and affects agent behavior.
6. The issue concerns an agent-specific runtime, sandbox, evaluator, trace, or orchestration component.

### Weak evidence

7. The issue occurs in a repository described as an "agent framework."
8. The issue mentions "agent" but the actual problem is generic infrastructure.

**Repository-level evidence alone is insufficient.**

---

# 7. Multi-Label Classification

An issue may belong to **multiple categories** when the same problem genuinely affects multiple agent-specific capabilities.

For example:

> "The agent repeatedly calls a tool because the tool result is not correctly inserted into the context."

Possible labels:

- **B.4 Misuse Tool Interfaces**
- **C.4 Short-Term Context Issues**
- **E.1 Single-Agent Inner Loop Issues**

However, the classifier should identify one **primary category** corresponding to the main root cause, followed by optional secondary categories.

Do not assign multiple labels merely because multiple components are mentioned.

---

# 8. Final Decision Rule

Classify a GitHub issue as an **Agent Issue** if:

1. The issue describes a real software problem, maintenance need, or feature request;
2. The problem affects an LLM-based agent system or its agent harness;
3. The affected functionality corresponds to at least one category in the taxonomy;
4. There is sufficient evidence that the issue affects an **agent-specific capability, execution path, or harness component**; and
5. The issue is not merely a generic software-engineering or infrastructure problem unrelated to agent behavior.

A **developer-committed patch is strong supporting evidence**, especially when the patch modifies LLM calls, prompts, memory, tools, orchestration, sandbox execution, tracing, evaluation, permissions, or other agent-harness components.

However, **the absence of a developer-committed patch should not by itself disqualify an issue** if the issue clearly satisfies the agent-specific definition.

---

# 9. Classification Output

For each GitHub issue, return:

- **Agent Issue:** Yes / No
- **Primary Category:** one taxonomy category
- **Secondary Categories:** zero or more
- **Harness Dimension:** one or more applicable Harness Engineering dimensions
- **Confidence:** High / Medium / Low
- **Evidence:** concise explanation based only on the issue and available repository information
- **Reason for Exclusion:** if classified as No

The final decision should prioritize **the actual technical nature of the issue over keywords**. Do not classify an issue as an agent issue simply because it contains words such as "agent", "LLM", "tool", or "memory".