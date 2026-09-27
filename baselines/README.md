Each folder is the `baseline/` directory from the checkout used in the comparison, not a full copy of that project.

`swe-bench-live/` belongs at `baseline/` inside a SWE-bench-Live tree. From that tree's root:

```bash
bash baseline/run_RQ1_sbl.sh
```

`swe-factory/` belongs at `baseline/` inside a SWE-Factory tree:

```bash
bash baseline/run_RQ1_swe-factory.sh baseline/issue_pr_map.json
```

`issue_pr_map.json` is the 225-issue pool. The numbered maps are the 10, 25, 50, 70, and 80-issue pilots. Both launch scripts still contain the conda path and checkout path of the machine that ran them.
