# RQ2: 判断 issue-PR 是否为 Agent Issue

本目录提供三种方法，用于判断给定 repo 中的 issue-PR 是否为 agent issue（论文 RQ2）。

## 目录与数据

```
SWEGENT-BENCH/Baseline/RQ2/
├── README.md                 # 本说明
├── issue_pr_map.json         # 问题列表（20 条）：repo / issue_number / pr_number
├── run_all.py                # 一键依次运行三种方法
├── rule_based/
│   ├── README.md
│   └── run_rule_based.py     # 方法 1：规则/关键词，复用 src/issue-hook
├── claude_agent/
│   ├── README.md
│   └── run_claude_agent.py   # 方法 2：Claude CLI，复用 issue-hook prompt
└── forge_ai/
    ├── README.md
    └── run_forge_ai.py       # 方法 3：Forge API，复用 issue-hook + forge
```

- **数据**：`issue_pr_map.json`（本目录下），每项 `{ "repo", "issue_number", "pr_number" }`。
- **脚本**：各子目录中的 `run_*.py`。

## 三种方法

| 方法 | 脚本 | 说明 |
|------|------|------|
| 1. 规则/启发式 | `rule_based/run_rule_based.py` | 复用 `src/issue-hook` 的 fetch + 规则判断，不调用 AI。 |
| 2. Claude Agent | `claude_agent/run_claude_agent.py` | 复用 issue-hook 拉取与 prompt，循环调用 `claude` CLI 得 yes/no。 |
| 3. 裸 AI (Forge) | `forge_ai/run_forge_ai.py` | 复用 issue-hook + `src/forge/api.py`，循环调用 LLM 得 yes/no。 |

## 输出格式

- 各方法在各自目录下生成 `YYYYMMDD_HHMMSS/<子目录>/`，单条结果：`<reponame>-<issue_number>.txt`，内容一行 `yes` 或 `no`。

## 运行

**一键跑三种方法**（推荐）：

```bash
cd /home/cc/SWEGENT-BENCH/Baseline/RQ2
python run_all.py
```

可选：`python run_all.py --limit 5`（只跑前 5 条）、`--token`、`--issue-pr-map`。

**单独跑某一方法**（默认用本目录 `issue_pr_map.json`）：

```bash
cd /home/cc/SWEGENT-BENCH/Baseline/RQ2/rule_based
python run_rule_based.py

cd ../forge_ai && python run_forge_ai.py
cd ../claude_agent && python run_claude_agent.py
```

各脚本还支持：`--issue-pr-map`、`--out-dir`、`--token`、`--limit`（见 `--help`）。

## 运行前准备

- **规则方法**：可访问 `src/issue-hook`、GitHub API（建议 `GITHUB_TOKEN`）。
- **Claude Agent**：已安装并配置 `claude` CLI。
- **Forge AI**：项目根 `.env` 配置 `FORGE_API_KEY`、`FORGE_BASE_URL`、`MODEL`。

详细见各子目录 `README.md`。
