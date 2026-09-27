These three scripts are the experiment entry points copied from the agent checkouts. Each one imports that agent's own code, so it has to be run from a checkout of the corresponding project, not from this folder alone.

| File | Run it from | Upstream |
| --- | --- | --- |
| `run_mini_swe_agent_batch.py` | a mini-SWE-agent checkout, as `exp/run_mini_swe_agent_batch.py` | `alfin06/mini-swe-agent` |
| `run_openhands_batch.py` | an OpenHands checkout, as `exp/run_openhands_batch.py` | `alfin06/OpenHands` |
| `run_acr_batch.py` | an AutoCodeRover checkout, as `exp/run_acr_batch.py` | `alfin06/auto-code-rover` |

`--artifacts-dir` is a directory of benchmark instances, one subdirectory per issue, matching `benchmark/` on Hugging Face. The commands are in the repository README.
