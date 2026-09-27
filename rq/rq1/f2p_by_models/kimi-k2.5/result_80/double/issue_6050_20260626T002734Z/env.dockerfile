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

# Install uv and make for build/test automation
RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Copy entire repository
COPY . .

# Install all packages in libs/*/ and docs/ if they contain pyproject.toml
# Assumption: Repository uses flat layout (not src/ layout) based on __init__.py paths in CI
# Assumption: Multiple packages exist in libs/*/ directories
RUN set -e; \
    for dir in libs/*/ docs/; do \
        if [ -d "$dir" ] && [ -f "$dir/pyproject.toml" ]; then \
            echo "Installing package in $dir"; \
            uv pip install --system -e "$dir" 2>/dev/null || pip install -e "$dir"; \
        fi; \
    done; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight check to verify testing infrastructure is available
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]