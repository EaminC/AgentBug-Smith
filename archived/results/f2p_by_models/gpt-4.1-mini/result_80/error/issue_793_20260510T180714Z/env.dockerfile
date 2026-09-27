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

# Set Forge API compatible environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key \
    PYTHONPATH=/app/src

# Set working directory
WORKDIR /app

# Copy entire repository into container
COPY . .

# Install system packages needed for Python builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc python3-dev libxml2-dev libxslt1-dev zlib1g-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel early
RUN python -m pip install --upgrade pip setuptools wheel

# Install poetry if poetry.lock and pyproject.toml exist
RUN if [ -f "poetry.lock" ] && [ -f "pyproject.toml" ]; then \
      pip install poetry; \
    fi

# Use poetry install with virtualenv disabled, install test deps
RUN if [ -f "poetry.lock" ] && [ -f "pyproject.toml" ]; then \
      poetry config virtualenvs.create false && poetry install; \
    fi

# Always install pytest test dependencies explicitly
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Install the local project in editable mode unconditionally
RUN pip install -e .

# Preflight test to confirm imports and pytest availability
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Final command to launch bash shell (test harness requirement)
CMD ["/bin/bash"]

# branch: python/poetry.lock + pyproject.toml, src/ layout