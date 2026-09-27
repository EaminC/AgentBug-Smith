# RQ2 方法 1：规则/启发式（Rule-based）

复用 `SWEGENT-BENCH/src/issue-hook` 中与 agent issue 相关的思路与 `agent_issue.md` 的指标，**仅用关键词与规则**判断，不调用任何 AI。

## 逻辑简述

- 从 `issue_pr_map.json` 读取 `repo`、`issue_number`（以及可选的 `pr_number`）。
- 用 GitHub API 拉取该 issue 的 title 与 body。
- 根据 `agent_issue.md` 中的指标（LLM provider、prompt、memory、tool、workflow 等）做关键词匹配；命中则判为 agent issue（yes），否则 no。
- 每个 issue 结果写入：`<时间戳>/rule_based/<reponame>-<issue_number>.txt`，内容单行 `yes` 或 `no`。

## 运行

```bash
cd /home/cc/SWEGENT-BENCH/Baseline/RQ2/rule_based
python run_rule_based.py
```

可选参数：

- `--issue-pr-map`：`issue_pr_map.json` 的路径，默认会尝试 `SWEGENT-BENCH/../swe-factory/baseline/issue_pr_map.json`，或环境变量 `RQ2_ISSUE_PR_MAP`。
- `--out-dir`：输出根目录，默认为本目录；其下会创建 `<时间戳>/rule_based/`。
- `--token`：GitHub token，也可设置环境变量 `GITHUB_TOKEN`。

## 依赖

- Python 3
- `requests`（若未安装：`pip install requests`）
- 可访问 GitHub API（建议配置 token 以免限流）
