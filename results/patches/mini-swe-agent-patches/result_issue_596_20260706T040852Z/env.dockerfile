FROM python:3.11-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_OPEN_INTERPRETER="0.0.1.dev0"
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="anthropic_base_url"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Install Poetry
RUN pip install poetry

# Configure Poetry to not create a virtual environment (use system Python)
ENV POETRY_VIRTUALENVS_CREATE=false

# Copy the entire repository
COPY . .

# Install project dependencies using Poetry
# Poetry will install dependencies from pyproject.toml
RUN if [ -f "pyproject.toml" ]; then \
        poetry install --no-interaction --no-ansi || pip install -e .; \
    else \
        pip install -e .; \
    fi

# Also ensure pip install -e . is run for good measure (works with pyproject.toml too)
RUN pip install -e .

# Install test dependencies explicitly
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout \
    setuptools litellm openai rich tiktoken astor gitpython tokentrim appdirs \
    six python-dotenv inquirer wget huggingface-hub pyyaml semgrep yaspin pyreadline3

# Install litellm and mem0ai as specified
RUN pip install litellm mem0ai

# Pre-flight check
RUN python -c "import interpreter; import pytest; print('preflight ok')"

# Default command
CMD ["/bin/bash"]

# Install mini-swe-agent and set configuration flag
RUN pip install --no-cache-dir mini-swe-agent && \
    mkdir -p /root/.config/mini-swe-agent && \
    echo "MSWEA_CONFIGURED=true" > /root/.config/mini-swe-agent/.env
