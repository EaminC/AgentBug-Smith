# Distribution of the 200-issue index

Total issues: **200**

Distinct repos: **11**

Distinct categories: **6** (A, B, C, D, E, F)

## Per-category counts

| category | count | share % |
|---|---:|---:|
| A | 34 | 17.0 |
| B | 58 | 29.0 |
| C | 38 | 19.0 |
| D | 15 | 7.5 |
| E | 33 | 16.5 |
| F | 22 | 11.0 |

## Per-repo counts (descending)

| repo | issues | share % | categories present |
|---|---:|---:|---|
| strands-agents/harness-sdk | 79 | 39.5 | A(12), B(28), C(11), D(8), E(12), F(8) |
| agentscope-ai/agentscope | 50 | 25.0 | A(6), B(22), C(6), D(3), E(9), F(4) |
| crewAIInc/crewAI | 24 | 12.0 | A(5), B(5), C(11), E(3) |
| MLSysOps/MLE-agent | 15 | 7.5 | A(2), B(1), C(5), E(3), F(4) |
| AntonOsika/gpt-engineer | 11 | 5.5 | A(3), C(2), D(2), E(2), F(2) |
| Aider-AI/aider | 8 | 4.0 | A(5), C(1), E(1), F(1) |
| langchain-ai/langgraph | 5 | 2.5 | C(1), E(1), F(3) |
| dapr/dapr-agents | 3 | 1.5 | B(1), E(2) |
| Significant-Gravitas/AutoGPT | 2 | 1.0 | A(1), B(1) |
| openinterpreter/open-interpreter | 2 | 1.0 | C(1), D(1) |
| strands-agents/sdk-python | 1 | 0.5 | D(1) |

## Category × repo cross-tab

| category | strands-agents/harness-sdk | agentscope-ai/agentscope | crewAIInc/crewAI | MLSysOps/MLE-agent | AntonOsika/gpt-engineer | Aider-AI/aider | langchain-ai/langgraph | dapr/dapr-agents | Significant-Gravitas/AutoGPT | openinterpreter/open-interpreter | strands-agents/sdk-python | total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 12 | 6 | 5 | 2 | 3 | 5 | 0 | 0 | 1 | 0 | 0 | **34** |
| B | 28 | 22 | 5 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | **58** |
| C | 11 | 6 | 11 | 5 | 2 | 1 | 1 | 0 | 0 | 1 | 0 | **38** |
| D | 8 | 3 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 1 | **15** |
| E | 12 | 9 | 3 | 3 | 2 | 1 | 1 | 2 | 0 | 0 | 0 | **33** |
| F | 8 | 4 | 0 | 4 | 2 | 1 | 3 | 0 | 0 | 0 | 0 | **22** |
| **total** | **79** | **50** | **24** | **15** | **11** | **8** | **5** | **3** | **2** | **2** | **1** | **200** |

## Repo size statistics

- min = 1, max = 79, mean = 18.2, median = 8
- size distribution: 1:1, 2:2, 3:1, 5:1, 8:1, 11:1, 15:1, 24:1, 50:1, 79:1

## Category entropy per repo

| repo | issues | # categories | entropy (nats) |
|---|---:|---:|---:|
| strands-agents/harness-sdk | 79 | 6 | 1.68 |
| agentscope-ai/agentscope | 50 | 6 | 1.55 |
| crewAIInc/crewAI | 24 | 4 | 1.27 |
| MLSysOps/MLE-agent | 15 | 5 | 1.49 |
| AntonOsika/gpt-engineer | 11 | 5 | 1.59 |
| Aider-AI/aider | 8 | 4 | 1.07 |
| langchain-ai/langgraph | 5 | 3 | 0.95 |
| dapr/dapr-agents | 3 | 2 | 0.64 |
| Significant-Gravitas/AutoGPT | 2 | 2 | 0.69 |
| openinterpreter/open-interpreter | 2 | 2 | 0.69 |
| strands-agents/sdk-python | 1 | 1 | -0.00 |
