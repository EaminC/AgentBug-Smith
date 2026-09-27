# Repo identity

**Repository Name:** MLE-Agent

**Description:** MLE-Agent is designed as a pairing LLM agent for machine learning engineers and researchers, enabling seamless AI engineering tasks.

---

# Typical issue shape

Typical issues revolve around memory-related behaviors, especially involving session resumption or restoration. Users often report difficulties in continuing previous sessions or encountering glitches.

---

# Recurring fix patterns

The most common fixes involve ensuring proper memory initialization and implementing caching mechanisms to store session states. This allows the agent to resume from previous steps effectively.

---

# Files / modules that change most often

- `mle/utils/cache.py`
- `mle/utils/system.py`
- `mle/workflow/baseline.py`

---

# Pitfalls

- Users may neglect initial memory setup, leading to issues in resuming sessions.
- Overlooking the state of cached content can result in incomplete functionality.

---

# Test conventions

Testing is primarily conducted in the `tests` directory using the frameworks defined in `.github/workflows/test.yml`. Unit tests focus on caching functionalities and workflow resumption processes.

---

# One concrete worked example

**Issue Title:** "Restarting previous session"

**Description:** This issue addresses the user's difficulty in resuming a previously started session due to a glitch in their system mid-session. 

For more details, see the issue [#121 here](https://github.com/MLSysOps/MLE-agent/issues/121).

