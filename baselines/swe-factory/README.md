# Baseline: End-to-End from Your Issue List

This folder contains scripts and a reference to run the SWE-Factory pipeline **starting from your own issue–PR mapping** (no “fetch top repos” or “fetch all PRs per repo”). All outputs use a **timestamp** so each run gets its own directories.

## Input format: `issue_pr_map.json`

A JSON array; each entry has exactly three fields:

| Field          | Type | Description        |
|----------------|------|--------------------|
| `repo`         | str  | `"owner/repo"`     |
| `issue_number` | int  | Issue number       |
| `pr_number`    | int  | Pull request number|

Example:

```json
[
  {"repo": "MLSysOps/MLE-agent", "issue_number": 273, "pr_number": 274},
  {"repo": "dapr/dapr-agents", "issue_number": 209, "pr_number": 279}
]
```

You only need to provide one such file; the script generates all intermediate and final paths with a timestamp.

---

## Quick start (one command)

From the **swe-factory repo root**:

```bash
export GITHUB_TOKEN=<your token>

./baseline/run_e2e_from_issue_map.sh baseline/issue_pr_map.json
```

Or with an absolute path:

```bash
./baseline/run_e2e_from_issue_map.sh /path/to/issue_pr_map.json
```

Pipeline steps (all automatic):

1. **fetch_prs_from_issue_map** – Fetch only the PRs in your map → `prs.jsonl`
2. **build_dataset** – Build task instances → `instances.jsonl`
3. **get_version** – Version tagging → `instances_versions.jsonl`
4. **SWE-Builder** – Build eval environments → `output/run_<ts>/results`
5. **run_evaluation** – Fail2Pass validation (gold)
6. **judge_fail2pass** – Classify and write report → `reports/run_<ts>_gold.json`

---

## Output layout (timestamped)

For a run at timestamp `YYYYMMDD_HHMMSS`:

| Path | Content |
|------|--------|
| `data/runs/<ts>/prs.jsonl` | Fetched PRs |
| `data/runs/<ts>/instances.jsonl` | Task instances |
| `data/runs/<ts>/instances_versions.jsonl` | Versioned instances |
| `output/run_<ts>/` | SWE-Builder output (incl. `results/results.json`) |
| `run_instances/run_<ts>/` | Fail2Pass run logs |
| `reports/run_<ts>_gold.json` | Fail2Pass classification (fail2pass / fail2fail / etc.) |

---

## Check counts after a run

To see how many items remain at each step (for a given run, override paths if needed):

```bash
python baseline/check_pipeline_counts.py
```

With custom paths (e.g. for a specific timestamped run):

```bash
python baseline/check_pipeline_counts.py \
  --prs data/runs/20260222_120000/prs.jsonl \
  --instances data/runs/20260222_120000/instances.jsonl \
  --instances_versions data/runs/20260222_120000/instances_versions.jsonl \
  --results output/run_20260222_120000/results/results.json \
  --fail2pass_report reports/run_20260222_120000_gold.json
```

---

## Manual step reference

See **`sf`** in this folder for the same pipeline as individual commands (with fixed paths, no timestamp). Use it when you want to run or debug a single step.

---

## One click to run script
```bash
./run_pipeline.sh baseline/issue_pr_map.json
```

## Instances with no in-patch test

`build_dataset.py` drops a PR when `test_patch` is empty. Two rebuttal3 launchers keep those PRs in the same pipeline. Everything after `instances.jsonl` is unchanged.

| Script | What it does |
|--------|----------------|
| `run_rebuttal3_swe-factory_keep_no_ipt.sh` | Rewrites `instances.jsonl` from `instances.jsonl.all`. Empty `test_patch` stays empty (`ipt_source=kept_empty`). |
| `run_rebuttal3_swe-factory_agentless_ipt.sh` | One chat completion per empty `test_patch` (Forge `MODEL` / `FORGE_API_KEY`, same client shape as `src/forge/api.py`). The reply is saved as `tests/agentless_ipt_<pr>.py` inside `test_patch`. A failed call falls back to a one-line placeholder so the instance is still kept. |

```bash
./run_rebuttal3_swe-factory_keep_no_ipt.sh baseline/issue_pr_map.json
./run_rebuttal3_swe-factory_agentless_ipt.sh baseline/issue_pr_map.json
```

The agentless test only exists so SWE-Builder sees an in-patch test. It is not a fail2pass oracle.

## Files in this folder

| File | Purpose |
|------|--------|
| `README.md` | This usage guide |
| `issue_pr_map.json` | Example/sample issue–PR map (3 fields per entry) |
| `run_e2e_from_issue_map.sh` | One-shot e2e script; input = one `issue_pr_map.json` |
| `run_RQ1_swe-factory.sh` | Original comparison runner (env, logs, cost tracker) |
| `run_rebuttal3_swe-factory_keep_no_ipt.sh` | Rebuttal3 runner that does not drop empty `test_patch` |
| `run_rebuttal3_swe-factory_agentless_ipt.sh` | Rebuttal3 runner that fills empty `test_patch` with one LLM call |
| `prepare_instances.py` | Shared step used by the two IPT launchers |
| `check_pipeline_counts.py` | Report per-step counts from pipeline JSON/JSONL |
| `sf` | Reference list of manual commands (no timestamping) |
