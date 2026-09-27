"""Train Cursor Agent Skills from RQ4's f2p-tested closed issues.

Public surface:

- :func:`utils.train.train_skill.main` — the orchestrator CLI.
- :mod:`utils.train.prompts` — the prompt templates sent to the
  per-repo agent.
- :doc:`utils/train/prompt.md` — design notes & rationale.

Six full runs populate ``agent/skills/{mini-swe-agent,openhands}/
{20,40,100}/`` with one skill per (agent, train-size).
"""
