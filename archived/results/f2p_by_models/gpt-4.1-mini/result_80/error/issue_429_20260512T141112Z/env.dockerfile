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

# Remove duplicate ENV declarations and unify environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Copy entire repository to container
COPY . .

# Upgrade pip, setuptools, wheel; install system dependencies for Python builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc python3-dev libpq-dev \
  && rm -rf /var/lib/apt/lists/* \
  && python -m pip install --upgrade pip setuptools wheel

# Install poetry if poetry files exist, else install test deps only
RUN if [ -f python/pyproject.toml ] && [ -f python/poetry.lock ]; then \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    cd python && poetry install --no-interaction --no-ansi && cd .. ; \
  fi

# Always install local packages in editable mode unconditionally
RUN pip install -e ./python

# Install test dependencies unconditionally
RUN pip install pytest pytest-mock pytest-xdist pytest-timeout anyio "setuptools<=81.0.0" litellm

# Set PYTHONPATH for imports if src layout is used
ENV PYTHONPATH=/app/python

# Preflight check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to open a Bash shell
CMD ["/bin/bash"]