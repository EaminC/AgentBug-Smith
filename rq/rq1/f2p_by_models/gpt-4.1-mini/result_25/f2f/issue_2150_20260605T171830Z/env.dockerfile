FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV GITHUB_TOKEN="ghp_key"
ENV HF_TOKEN="hf_key"
# --- end inject ---

# Set standard working directory
WORKDIR /app

# Set Forge environment variables (corrected ANTHROPIC_BASE_URL to include /v1)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Copy entire repository
COPY . .

# Upgrade pip and setuptools first
RUN python -m pip install --upgrade pip setuptools wheel

# Install local package(s) in editable mode unconditionally
RUN pip install -e .

# Install requirements if present
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install poetry and dependencies if pyproject.toml and poetry.lock exist
RUN if [ -f pyproject.toml ] && [ -f poetry.lock ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi; \
    fi

# Install test and runtime dependencies unconditionally
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to fail fast if modules missing
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set PYTHONPATH explicitly to /app for source imports
ENV PYTHONPATH=/app

# Final command as inferred from pyproject.toml scripts and repo structure:
# The main entrypoint python script is src/my_project/main.py
CMD ["python", "src/my_project/main.py"]