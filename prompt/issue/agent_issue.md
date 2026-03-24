## 1. Definition of an Agent Issue

An **agent issue** refers to a user-reported problem (e.g., a bug report or a feature request) that occurs in an LLM-based agent system and that is related to components or behaviors unique to agent systems. According to the paper, agent issues include failures or maintenance needs tied to LLM provider integration, tool invocation, memory mechanisms, LLM operation, workflows, and utilities within agent systems.


 

## 2. Taxonomy of Agent Issues

Here we presents a taxonomy consisting of **6 major categories** and **20 sub-categories**. Below is the taxonomy as reported.

### A. Incompatibility with LLM providers  

* **Incompatible dependencies**: Missing, misuse or improperly installed the third-party libraries of model providers, such as the openai python library or litellm library.
* **Unsupported models**: Problems where the agent is unable to support or work with popular LLM models, such as DeepSeek R1, GPT-4 Turbo, Claude 3.5, and etc., preventing their use within the agent system for specific tasks.
* **Incompatible parameters to LLM providers**: Providing unexpected parameters or missing necessary parameters when invoking the LLM from third-party LLM providers, such as OpenAI, Anthropic, Together AI, or others.

### B. Tool-related issues  

* **Tool dependency issues**: Failures caused by missing, incompatible, or misconfigured software dependencies (such as libraries, modules, drivers, or external binaries) that are essential for the agent's tool-handling capabilities and for the agent's tool to function properly. This category includes any dependency error (e.g., ModuleNotFoundError, TypeError) that prevents the definition, parsing, registration, or runtime execution of tools.
* **Tool configuration issues**: Misconfigurations in tool-related settings, such as retrieval mode selection, retriever assignment, or embedder specification.
* **Tool implementation errors**: Flaws in the execution logic of self-developed tools or tool systems (e.g., RAG). This category includes bugs, unhandled edge cases like empty outputs or token limits, or incorrect logic found within a tool's main function as well as in any internal helper, processing, or utility functions that the tool relies on to operate correctly (e.g., functions for text splitting, data parsing, or file handling).
* **Misuse tool interfaces**: Errors that prevent the tool from being called correctly, such as missing or unexpected or malformed parameters, errors originating from the underlying data structures or types or utility classes used to define or pass or process tool arguments (e.g., issues with serialization, hashability, or other required protocols), and flawed logic in binding tools to LLMs.

### C. Memory-related issues  

* **Memory initialization issues**: Failures in properly initializing or resetting memory components, such as issues with database initialization, workspace resetting, or the improper application of uploaded files to new workspaces, leading to incomplete or inconsistent memory states.
* **Memory content errors**: Inaccuracies or inconsistencies in memory representation, including erroneous message attributes, redundant content, and flawed implementation of any agent-related storage mechanism (such as for messages, intermediate states, or task outputs). This category explicitly includes failures in storing, retrieving, or processing data from these storage systems due to data type incompatibilities or serialization/deserialization errors, particularly when the storage cannot natively handle specific non-primitive types or complex data structures.
* **Memory dependency issues**: Failures caused by changes or inconsistencies in internal modules or external dependencies required for memory operations.

### D. LLM operation issues 

* **Model access misconfiguration**: Misconfigurations that prevent proper access to the intended model, such as incorrect model binding or missing authentication credentials (e.g., API keys).
* **Token usage misconfiguration**: Failures in setting token-related parameters for LLMs, such as maximum token limits, token pricing, or token management modules, which may lead to inference errors or cost tracking failures.
* **Incorrect model output handlers**: Errors in parsing standard LLM responses or failing to manage exceptional outputs, such as empty results, malformed data, refusal to answer, or other unexpected behaviors.
* **Model dependency issues**: Issues arising from dependency management problems (such as missing, optional, or incompatible libraries) that prevent or hinder the proper functioning of the LLM or its related components. This scope explicitly includes libraries required for tokenization (e.g., tiktoken), interfacing with model provider APIs, or core model-handling operations.
* **Context length issues**: Errors arising from exceeding the LLM's maximum context length or incorrect calculations of the context length, leading to validation errors or output failures.
* **Prompt-related issues**: Suboptimal prompt content or prompt management issues (e.g., failure to set or update prompts).

### E. Workflow issues  

* Problems in the scheduling or execution of an agent's workflow, leading to errors such as hanging, infinite loops, or skipped steps in the process.

### F. Utility issues

* **Utility implementation issues**: Errors arising from the faulty implementation of non-LLM components in the agent system, such as UI, Docker, logging, library's import (e.g., time) or other auxiliary utilities that support the agent's operation.
* **Utility dependency issues**: Problems arising from missing dependencies or incompatible dependencies unrelated to the agent or agent tools, such as external libraries for file handling or testing and circular dependencies between internal modules.
* **Utility configuration issues**: Problems arising from incorrect or missing configuration of external components unrelated to the agent, such as I/O settings (e.g., file paths and encoding) or network settings like IP addresses or observability/telemetry systems (e.g., OpenTelemetry).

 
## 3. Indicators that an Issue is an Agent Issue

According to your analysis and inclusion criteria, the following signals indicate that a GitHub issue likely qualifies as an agent issue:

* The issue is tied to LLM provider usage (e.g., SDK parameters, model names, provider authentication).
* The issue references prompt behaviors, prompt templates, or incorrect prompt management.
* The issue concerns memory behaviors (e.g., incorrect storage, missing history, content corruption).
* The issue involves tool invocation failures, tool configuration, or tool implementation errors.
* The issue reports workflow anomalies (e.g., hanging agent loop, repeated tasks, failed orchestrations).
* The issue includes developer-committed patches that change code in the aforementioned agent-specific components.
* The issue does not fall under Utility Issues, including Utility implementation issues, Utility dependency issues, and Utility configuration issues.

 

## 4. Practical Checklist to Decide if an Issue is an Agent Issue

* Does the issue explicitly reference an LLM provider, model name, SDK, or API key? (Yes → Agent Issue)
* Does the issue mention prompt content, prompt templates, or prompt management problems? (Yes → Agent Issue)
* Does the issue report memory-related symptoms (missing history, corrupted stored content, initialization issues)? (Yes → Agent Issue)
* Does the issue involve tool invocation, tool parameters, tool configuration, or tool implementation errors? (Yes → Agent Issue)
* Does the issue describe agent workflow anomalies (hangs, loops, unexpected repeated actions)? (Yes → Agent Issue)
* Is the issue resolved by a developer patch that changes components such as LLM calls, memory store logic, tool wrappers, prompt templates, or orchestration code? (Yes → Agent Issue)

If at least one of the above is true and the issue is closed with a developer-committed patch addressing that concern, the issue aligns with the definition of an agent issue.