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

# Install system build dependencies required for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Install requirements.txt if it exists (conditional safe operation)
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Editable install of main package
RUN pip install -e .

# Handle monorepo structure: install sub-packages in libs/ or packages/ or src/
RUN for dir in libs/* packages/* src/*/; do \
    if [ -d "$dir" ] && ([ -f "$dir/setup.py" ] || [ -f "$dir/pyproject.toml" ]); then \
        pip install -e "$dir" || echo "Warning: Failed to install $dir"; \
    fi; \
done 2>/dev/null || true

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include potential source directories for multi-package repos
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages

# Preflight verification to ensure core tooling is available
RUN python -c "import pytest; print('preflight ok')"

CMD ["/bin/bash"]