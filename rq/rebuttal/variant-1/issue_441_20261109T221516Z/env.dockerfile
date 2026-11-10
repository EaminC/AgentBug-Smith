FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Copy entire repo
COPY . .

# Install system dependencies needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies and install the project
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt && pip install -e . ; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi && \
        pip install -e . ; \
    elif [ -f "pyproject.toml" ]; then \
        pip install -e . ; \
    else \
        echo "No recognized Python package manager files found." ; exit 1 ; \
    fi

# Install test dependencies excluding pytest-block-network due to unavailability
RUN pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm "ollama>=0.1.7"

# Preflight test for installed modules
RUN python -c 'import pkg_resources, pytest, ollama; print("preflight ok")'

# Set PYTHONPATH for repo layout
ENV PYTHONPATH=/app:/app/src

# Set environment variables for Forge API (OpenAI-compatible) and Anthropic SDK
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Expose FORGE_API_KEY as an environment variable with actual value
ENV FORGE_API_KEY="forge-key"

# Default command to open bash shell
CMD ["/bin/bash"]

# branch: python with requirements.txt / pyproject.toml, no pytest-block-network, Forge env vars set
