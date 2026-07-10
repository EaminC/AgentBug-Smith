FROM python:3.11-slim

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

# Set Forge API environment variables for OpenAI compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key

# Set Forge API environment variables for Anthropic compatibility
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Additional environment variables
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Pre-flight check
RUN python -c "import interpreter; import pytest; print('preflight ok')"

# Default command
CMD ["/bin/bash"]
