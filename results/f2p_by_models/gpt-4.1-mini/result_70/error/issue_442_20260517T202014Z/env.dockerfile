FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev python3-dev rustc cargo \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and set compatible setuptools version
RUN python -m pip install --upgrade pip setuptools==81.0.0 wheel

# Copy entire repository
COPY . .

# Workaround: prebuild multidict wheel to avoid poetry install build failures
RUN python -m pip wheel multidict==6.0.4 || true

# Install dependencies using poetry if present, else fallback to requirements.txt
RUN if [ -f poetry.lock ]; then \
      python -m pip install poetry && \
      poetry config virtualenvs.create false && \
      poetry install --no-interaction --no-ansi; \
    elif [ -f requirements.txt ]; then \
      python -m pip install -r requirements.txt; \
    fi

# Install local project and all sub-packages in editable mode unconditionally
# Adjust these paths if your repo has multiple packages under libs/ or packages/
RUN pip install -e . 

# Install standard test dependencies
RUN python -m pip install pytest pytest-mock pytest-xdist pytest-timeout litellm

# Explicitly set PYTHONPATH to include main app and possible sub-packages
ENV PYTHONPATH=/app

# Verify installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]

# branch: python/poetry-fix-multidict-forge-env