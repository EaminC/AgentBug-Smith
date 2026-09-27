#!/bin/bash
# 示例：使用不同配置运行工具

# 示例1: 快速测试（2个仓库，限制输出）
echo "示例1: 快速测试"
python main.py \
  --keywords awesome-agent \
  --min-stars 100 \
  --max-awesome-repos 2 \
  --limit 20

echo ""
echo "================================"
echo ""

# 示例2: 完整运行（默认配置）
# python main.py

# 示例3: 多关键词搜索
# python main.py \
#   --keywords awesome-agent awesome-llm awesome-ai-agents awesome-chatgpt \
#   --min-stars 50 \
#   --max-awesome-repos 10

# 示例4: 高质量仓库（高star要求）
# python main.py \
#   --keywords awesome-agent awesome-llm \
#   --min-stars 200 \
#   --max-awesome-repos 15



