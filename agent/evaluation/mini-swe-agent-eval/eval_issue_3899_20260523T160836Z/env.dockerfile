FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Detect src/ layout (used for install decision)
RUN SRC_LAYOUT=0 && \
    if [ -d "src" ] || grep -Rq "^\s*from src\.\|^\s*import src\." . 2>/dev/null; then \
      SRC_LAYOUT=1; \
    fi && \
    # Install dependencies and the project
    if [ -f "requirements.txt" ]; then \
      if [ "$SRC_LAYOUT" -eq 1 ]; then \
        pip install -r requirements.txt; \
      else \
        pip install -r requirements.txt && pip install -e .; \
      fi; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
      pip install poetry && \
      poetry config virtualenvs.create false && \
      poetry install --no-interaction --no-ansi && \
      if [ "$SRC_LAYOUT" -eq 0 ]; then \
        pip install -e .; \
      fi; \
    elif [ -f "pyproject.toml" ]; then \
      if [ "$SRC_LAYOUT" -eq 0 ]; then \
        pip install -e .; \
      fi; \
    fi && \
    # Explicitly install sub-packages so they're importable during tests
    pip install -e lib/crewai && \
    pip install -e lib/crewai-tools && \
    # Always install test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout litellm "setuptools<=81.0.0" mem0ai

# If src layout is detected, set PYTHONPATH to avoid import issues
ENV PYTHONPATH=/app

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Export the FORGE_API_KEY as well
ENV FORGE_API_KEY="forge-key"

CMD ["/bin/bash"]

# branch: python/requirements.txt or pyproject.toml