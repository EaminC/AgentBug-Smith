# Component 2 — OpenHands CLI

Upstream: <https://github.com/OpenHands/OpenHands-CLI>
Installed via (separate, one-time): `curl -fsSL https://install.openhands.dev/install.sh | sh`
API gateway: <https://api.tu-zi.com> (OpenAI-compatible)

## Why CLI, not Agent Canvas

The npm-based [`@openhands/agent-canvas`](https://www.npmjs.com/package/@openhands/agent-canvas)
spins up a web UI on port 8000. That's GUI. We want the same one-shot
shape as component 1 (CLI takes a task, makes the changes, exits). The
official `OpenHands-CLI` binary has a headless mode that matches.

## Boundary

| Layer | Owner | Tracked? |
| --- | --- | --- |
| `openhands` binary (`~/.local/bin/openhands`) | OpenHands installer | **No** (system-level) |
| `config/`, `run_openhands.sh` | **RQ4** | Yes |

## Files

- `run_openhands.sh` (parent dir) — sources `.env`, then runs
  `openhands --headless --override-with-envs --yolo "$@"`.
- `.env` — `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`. Gitignored, `chmod 600`.
- `.env.example` — template.
- `smoke_test.sh` — issues a tiny task, verifies the artifact.

## Usage

```bash
# one-time bootstrap (assuming the binary is already installed)
bash scripts/setup-openhands.sh

# run a task — same shape as component 1
bash agent/run_openhands.sh -t "fix the failing test in src/foo.py"
```

> `--yolo` is auto-appended by the wrapper. Headless mode already
> always auto-approves actions, so this is just defensive.
