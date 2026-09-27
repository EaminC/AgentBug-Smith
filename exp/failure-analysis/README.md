# Failure-mode labels

Each unsuccessful reproduction run (not `f2p`, not the `double/` copy of a later success) was labeled by GPT with no predefined category list. Phrases were grouped afterwards.

| Cluster | DeepSeek | GPT-4.1-mini | Kimi-k2.5 |
|---|---:|---:|---:|
| Dependency installation | 48 | 36 | 21 |
| Docker build configuration | 22 | 15 | 40 |
| Missing imports or incompatible APIs | 21 | 33 | 9 |
| Python packaging metadata | 15 | 27 | 4 |
| Native build or compiler | 14 | 28 | 5 |
| Container disk exhaustion | 12 | 0 | 40 |
| Missing verifier or Docker logs | 15 | 12 | 56 |
| Test or application behavior | 15 | 29 | 4 |
| Total | 162 | 180 | 179 |

`open_labels.jsonl` has one row per run (`backbone`, `pool`, `folder`, `issue`, `failure`, `note`).
