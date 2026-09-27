# Agent components

Each subdirectory is a self-contained RQ4 component. See the table in the
top-level [README](../README.md) for the current list.

## Component 1 — `mini-swe-agent`

Wraps [`SWE-agent/mini-swe-agent`](https://github.com/SWE-agent/mini-swe-agent)
and routes it through the shared tu-zi OpenAI-compatible gateway.

### Boundary

| Layer | Owner | Tracked? |
| --- | --- | --- |
| `mini-swe-agent/` (cloned from upstream) | upstream | **No** |
| `.venv/` (Python venv) | local | **No** |
| `config/`, `run_mini.sh` | **RQ4** | Yes |

We only ever edit files tracked in git. `scripts/setup.sh` will refuse to
overwrite an existing upstream clone whose `origin` is not the official
`SWE-agent/mini-swe-agent` — this catches accidental in-place edits.

### Files

- `run_mini.sh` — single entry point. Sources `config/.env`, activates the
  venv, then `exec`s the `mini` CLI with both the built-in `mini.yaml`
  and our `config/mini.yaml` so defaults aren't clobbered.
- `config/mini.yaml` — user-customizable extension point (intentionally
  empty by default; CLI flags cover `cost-limit` and `mode`).
- `config/.env` — real API key + base URL (gitignored, `chmod 600`).
- `config/.env.example` — template for the above.
- `config/smoke_test.py` — single round-trip tool-call verification.

### Usage

```bash
# one-time bootstrap
bash scripts/setup.sh

# run a task
bash agent/run_mini.sh -t "fix the failing test in src/foo.py" -m openai/gpt-4o-mini

# run the smoke test by hand
source agent/config/.env
source agent/.venv/bin/activate
python agent/config/smoke_test.py
```

## Component 2 — `openhands` CLI

Wraps [`OpenHands/OpenHands-CLI`](https://github.com/OpenHands/OpenHands-CLI),
the official lightweight CLI binary. Headless mode gives us the same
one-shot shape as component 1: the CLI takes a task, makes the changes,
exits.

### Boundary

| Layer | Owner | Tracked? |
| --- | --- | --- |
| `openhands` binary (`~/.local/bin/openhands`) | OpenHands installer | **No** (system-level) |
| `openhands-config/`, `run_openhands.sh` | **RQ4** | Yes |

### LLM configuration

We use `--override-with-envs` to pass `LLM_API_KEY` / `LLM_BASE_URL` /
`LLM_MODEL` from `openhands-config/.env` directly to the CLI on every
run. No browser-based setup needed.

See `openhands-config/README.md` for the canonical explanation.

### Files

- `run_openhands.sh` — sources `openhands-config/.env` and `exec`s
  `openhands --headless --override-with-envs --yolo "$@"`.
- `openhands-config/.env` — `LLM_API_KEY` / `LLM_BASE_URL` /
  `LLM_MODEL`. Gitignored, `chmod 600`.
- `openhands-config/.env.example` — template.
- `openhands-config/README.md` — component explanation.
- `openhands-config/smoke_test.sh` — issues a real headless task and
  verifies the created artifact. Catches breakage in CLI ↔ gateway ↔
  sandbox wiring end-to-end.

### Usage

```bash
# one-time install (not managed by this repo)
curl -fsSL https://install.openhands.dev/install.sh | sh

# bootstrap (writes .env, runs smoke test)
bash scripts/setup-openhands.sh

# run a task
bash agent/run_openhands.sh -t "fix the failing test in src/foo.py"