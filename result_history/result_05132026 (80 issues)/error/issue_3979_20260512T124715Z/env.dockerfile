FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set working directory
WORKDIR /app

# Set environment variables for Forge API compatibility and Python execution
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tensorblock/gpt-4.1-mini" \
    AI_TEMPERATURE="0.7" \
    GITHUB_TOKEN="ghp_key" \
    TAVILY_API_KEY="tvly-key" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Install system dependencies needed to build Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libyaml-dev \
    git \
  && rm -rf /var/lib/apt/lists/*

# Copy entire repository contents
COPY . .

# Upgrade pip, setuptools, and wheel early
RUN python -m pip install --upgrade pip setuptools wheel

# Upgrade setuptools explicitly to avoid build errors, then install dependencies
RUN pip install --upgrade setuptools && \
    if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt; \
    elif [ -f "pyproject.toml" ]; then \
      pip install poetry && \
      poetry config virtualenvs.create false && \
      poetry install --no-interaction --no-ansi; \
    else \
      echo "No requirements.txt or pyproject.toml found; skipping dependency installation"; \
    fi

# Install the project itself in editable mode unconditionally
RUN pip install -e .

# Install standard Python test dependencies as required
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Run a simple check to verify the environment is set up correctly
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to start a bash shell
CMD ["/bin/bash"]