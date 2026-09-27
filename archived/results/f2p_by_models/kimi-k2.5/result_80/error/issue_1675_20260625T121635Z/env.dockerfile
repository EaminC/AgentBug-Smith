FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Set PYTHONPATH to handle both root and potential src layouts
ENV PYTHONPATH=/app:/app/src:/app/libs/agentscope

COPY . .

# Install dependencies with robust handling for monorepo structures
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    # Install main package in editable mode
    pip install -e . && \
    # Handle potential monorepo sub-packages (common patterns)
    if [ -f libs/agentscope/setup.py ] || [ -f libs/agentscope/pyproject.toml ]; then \
        pip install -e libs/agentscope; \
    fi && \
    if [ -f packages/agentscope/setup.py ] || [ -f packages/agentscope/pyproject.toml ]; then \
        pip install -e packages/agentscope; \
    fi && \
    # Install test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Verify installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")' && \
    python -c 'from agentscope.formatter import DashScopeChatFormatter; print("import ok")' || echo "Warning: DashScopeChatFormatter not found in expected location"

CMD ["/bin/bash"]