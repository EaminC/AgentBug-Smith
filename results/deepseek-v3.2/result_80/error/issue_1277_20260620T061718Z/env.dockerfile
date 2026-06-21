FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Set PYTHONPATH for src/ layout
ENV PYTHONPATH=/app

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository
COPY . .

# Install requirements if they exist
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi

# Install the project in editable mode (CRITICAL)
RUN pip install -e .

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

# Install additional dependencies that might be needed
RUN pip install aioitertools anthropic dashscope docstring_parser json5 json_repair mcp>=1.13 numpy openai python-datauri opentelemetry-api>=1.39.0 opentelemetry-sdk>=1.39.0 opentelemetry-exporter-otlp>=1.39.0 opentelemetry-semantic-conventions>=0.60b0 python-socketio shortuuid tiktoken sounddevice sqlalchemy python-frontmatter

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]