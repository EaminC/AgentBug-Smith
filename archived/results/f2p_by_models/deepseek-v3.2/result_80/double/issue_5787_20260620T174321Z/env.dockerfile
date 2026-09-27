FROM python:3.12-slim AS test_builder

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

# Copy entire repository
COPY . .

# Check for package manager files and install dependencies
# Based on evidence: the project uses uv (Makefile, CI workflows) and has pyproject.toml.
# We'll install uv, sync dependencies, and install test packages.
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.cargo/bin/uv /usr/local/bin/uv && \
    # Install dependencies using uv sync (as seen in CI workflows)
    uv sync --group dev --frozen && \
    # Install additional test dependencies (mandatory)
    uv pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# CRITICAL: Install the local project in editable mode
RUN pip install -e .

# CRITICAL: Set PYTHONPATH for multi-package layouts
# Check repository structure and set PYTHONPATH accordingly
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:$PYTHONPATH

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]