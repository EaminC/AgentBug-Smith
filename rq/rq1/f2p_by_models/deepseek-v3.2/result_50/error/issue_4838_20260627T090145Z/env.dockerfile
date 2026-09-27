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

# Install system dependencies needed for the project
RUN apt-get update && apt-get install -y \
    curl jq wget git \
    chromium-driver firefox-esr ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PIP_NO_CACHE_DIR=yes \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Copy entire repository (mandatory)
COPY . .

# Determine package manager and install dependencies
# The repository includes both requirements.txt and pyproject.toml.
# The existing Dockerfile uses pip install -r requirements.txt, so we follow that.
RUN python -m pip install --upgrade pip wheel && \
    # Install requirements.txt if it exists
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    # Install test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai && \
    # Install the project itself in editable mode
    pip install -e .

# For multi-package layouts, also install any sub-packages
# Check for common multi-package structures
RUN if [ -d "libs" ]; then \
        for dir in libs/*/; do \
            if [ -f "$dir/setup.py" ] || [ -f "$dir/pyproject.toml" ]; then \
                pip install -e "$dir"; \
                export PYTHONPATH="$PYTHONPATH:/app/$dir"; \
            fi; \
        done; \
    fi

RUN if [ -d "packages" ]; then \
        for dir in packages/*/; do \
            if [ -f "$dir/setup.py" ] || [ -f "$dir/pyproject.toml" ]; then \
                pip install -e "$dir"; \
                export PYTHONPATH="$PYTHONPATH:/app/$dir"; \
            fi; \
        done; \
    fi

# Update PYTHONPATH environment variable
ENV PYTHONPATH=/app:$PYTHONPATH

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command (as per the existing Dockerfile entrypoint, but we override for testing)
CMD ["/bin/bash"]