# RQ2 方法 2：Claude Code Agent

使用 **Claude Code**（`claude` CLI）逐个判断 issue 是否为 agent issue：  
用 GitHub API 拉取 issue 上下文，循环调用 `claude -p --dangerously-skip-permissions`，只让 agent 回答当前 repo/issue 是否为 agent issue（yes/no），并写入结果文件。

## 输出

- 目录：`<时间戳>/claude/`（时间戳在每次运行开始时生成）。
- 文件：`<reponame>-<issue_number>.txt`（如 `MLSysOps-MLE-agent-273.txt`），内容单行 `yes` 或 `no`。

## 前置条件

- 已安装并配置 `claude` CLI（可交互或非交互执行）。
- 使用 `--dangerously-skip-permissions` 以便 agent 将答案写入上述文件。
- 建议设置 `GITHUB_TOKEN` 以拉取 issue。

## 运行

```bash
cd /home/cc/SWEGENT-BENCH/Baseline/RQ2/claude_agent
python run_claude_agent.py
```

可选参数：

- `--issue-pr-map`：`issue_pr_map.json` 路径。
- `--out-dir`：输出根目录，其下会创建 `<时间戳>/claude/`。
- `--token`：GitHub token（或 `GITHUB_TOKEN`）。
- `--limit N`：只处理前 N 条（例如 20 条做快速测试）。

示例（只跑前 20 个）：

```bash
python run_claude_agent.py --limit 20
```

## 依赖

- Python 3、`requests`
- 系统已安装 `claude` 且可用
