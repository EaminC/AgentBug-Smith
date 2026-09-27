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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:$PYTHONPATH

# Determine package manager and install dependencies
# Based on the Makefile and CI workflows, this project uses uv.
# We check for uv.lock and pyproject.toml.
RUN python -m pip install --upgrade pip wheel && \
    if [ -f uv.lock ]; then \
        pip install uv && \
        uv pip install -e . --group dev; \
    elif [ -f pyproject.toml ]; then \
        pip install -e .; \
    else \
        echo "No pyproject.toml or uv.lock found." && exit 1; \
    fi && \
    # Install any sub-packages in editable mode
    if [ -d libs ]; then \
        find libs -name "pyproject.toml" -o -name "setup.py" | while read f; do \
            dir=$(dirname "$f"); \
            pip install -e "$dir"; \
        done; \
    fi && \
    if [ -d packages ]; then \
        find packages -name "pyproject.toml" -o -name "setup.py" | while read f; do \
            dir=$(dirname "$f"); \
            pip install -e "$dir"; \
        done; \
    fi && \
    # Mandatory test framework installation
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight check to ensure core modules are importable
RUN python -c 'import langgraph; import pytest; print("preflight ok")'

# The project's Makefile indicates the test command is 'make test'.
# We'll run that as part of the test stage (but the final CMD is bash for the test harness).
# The final CMD is inferred from the project's configuration: the Makefile target 'test' is the standard.
# However, the test harness expects a bash shell for interactive test injection.
CMD ["/bin/bash"]