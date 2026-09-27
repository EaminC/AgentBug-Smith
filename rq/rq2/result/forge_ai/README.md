# RQ2 方法 3：裸 AI（Forge API）

使用 **SWEGENT-BENCH/src/forge/api.py** 的 LLM 接口，循环对每个 issue 提供上下文，只要求回答 yes 或 no，结果由程序写入文件。

## 输出

- 目录：`<时间戳>/forge/`
- 文件：`<reponame>-<issue_number>.txt`，内容单行 `yes` 或 `no`。

## 前置条件

- 在 **SWEGENT-BENCH 项目根** 配置 `.env`：
  - `FORGE_API_KEY`、`FORGE_BASE_URL`、`MODEL`（参见 `.env.example`）
- 建议设置 `GITHUB_TOKEN` 以拉取 issue。

## 运行

```bash
cd /home/cc/SWEGENT-BENCH/Baseline/RQ2/forge_ai
python run_forge_ai.py
```

可选参数：

- `--issue-pr-map`：`issue_pr_map.json` 路径。
- `--out-dir`：输出根目录。
- `--token`：GitHub token（或 `GITHUB_TOKEN`）。
- `--limit N`：只处理前 N 条。

示例：

```bash
python run_forge_ai.py --limit 20
```

## 依赖

- Python 3、`requests`、`openai`、`python-dotenv`
- 项目根下 `src/forge/api.py` 可用
