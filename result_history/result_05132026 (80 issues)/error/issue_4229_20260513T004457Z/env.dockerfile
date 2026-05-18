# syntax=docker/dockerfile:1.4

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

# Set environment variables for Forge API compatibility
ENV FORGE_API_KEY=forge-key
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Install system dependencies needed for building Python packages and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc python3-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev libyaml-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repo into container
COPY . .

# Upgrade pip, setuptools, wheel, and fix PyYAML wheel build issues
RUN python -m pip install --upgrade pip setuptools==81.0.0 wheel

# Install dependencies from requirements.txt if present
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt ; \
    fi

# Install poetry dependencies if pyproject.toml and poetry.lock present
RUN if [ -f pyproject.toml ] && [ -f poetry.lock ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi ; \
    fi

# Install local package in editable mode unconditionally
RUN pip install --no-cache-dir -e .

# Install standard test dependencies explicitly
RUN pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout litellm setuptools<=81.0.0

# Set PYTHONPATH to include all source directories if multi-package repo detected
# (Adjust these paths if your repo structure differs)
ENV PYTHONPATH=/app:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Verify key imports work
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]