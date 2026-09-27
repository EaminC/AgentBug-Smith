FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages

WORKDIR /app

# Install system dependencies for crewai (from README troubleshooting)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Install uv for dependency management
RUN pip install uv

# Create virtual environment and install dependencies
RUN uv venv && \
    uv sync --dev --all-extras

# Install the local project in editable mode (CRITICAL)
RUN pip install -e .

# Install mandatory testing dependencies
RUN pip install pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Safe installation of requirements.txt if it exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Safe installation of requirements-dev.txt if it exists
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

# Safe installation of dev-requirements.txt if it exists
RUN if [ -f dev-requirements.txt ]; then pip install -r dev-requirements.txt; fi

# Preflight import check
RUN python -c "import crewai, pytest; print('preflight ok')"

# Default command to run tests
CMD ["pytest", "-v", "--tb=short"]