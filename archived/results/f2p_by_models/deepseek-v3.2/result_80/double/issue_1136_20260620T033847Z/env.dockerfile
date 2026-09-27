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

# Set required environment variables for Forge
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Upgrade packaging tools first
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository
COPY . .

# Set PYTHONPATH to include the project root
ENV PYTHONPATH=/app

# Install the project in editable mode with dev dependencies
RUN if [ -f "pyproject.toml" ]; then \
        pip install -e .[dev]; \
    elif [ -f "setup.py" ]; then \
        pip install -e .; \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm fakeredis aiosqlite greenlet; \
    else \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm fakeredis aiosqlite greenlet; \
    fi

# Preflight check to ensure core modules can be imported
RUN python -c 'import pkg_resources, pytest, agentscope; print("preflight ok")'

CMD ["/bin/bash"]