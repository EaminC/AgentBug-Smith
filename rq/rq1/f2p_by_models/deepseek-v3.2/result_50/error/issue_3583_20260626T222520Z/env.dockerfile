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

# Install system dependencies for browsers and utilities (from original Dockerfile)
RUN apt-get update && apt-get install -y \
    chromium-driver firefox-esr \
    ca-certificates curl jq wget git \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=yes \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="$PATH:/root/.local/bin" \
    PYTHONPATH="/app:$PYTHONPATH"

# Copy entire repository (mandatory for test script injection)
COPY . .

# Determine package manager and install dependencies
# Evidence: requirements.txt exists, pyproject.toml exists, no poetry.lock
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    # Check for multi-package layout and install sub-packages
    if [ -d "src" ]; then \
        find src -name "setup.py" -o -name "pyproject.toml" | while read pkg; do \
            pkg_dir=$(dirname "$pkg"); \
            pip install -e "$pkg_dir"; \
        done; \
    fi && \
    # Install the project itself (editable install)
    if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then \
        pip install -e .; \
    fi && \
    # Mandatory test framework and additional dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH for multi-package layouts
RUN if [ -d "src" ]; then \
        export_paths=$(find src -type d -name "__pycache__" -prune -o -type f -name "*.py" -exec dirname {} \; | sort -u | sed 's|^|/app/|' | tr '\n' ':' | sed 's/:$//'); \
        echo "PYTHONPATH=\$PYTHONPATH:$export_paths" >> /etc/environment; \
    fi

# Preflight import check
RUN python -c "import pytest; print('pytest version:', pytest.__version__); print('preflight ok')"

# Final command (as required by test harness)
CMD ["/bin/bash"]