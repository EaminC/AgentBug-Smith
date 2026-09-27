FROM python:3.12-slim

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
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout litellm "setuptools<=81.0.0" mem0ai a2a-sdk

# If src layout is detected, set PYTHONPATH to avoid import issues
ENV PYTHONPATH=/app

CMD ["/bin/bash"]
