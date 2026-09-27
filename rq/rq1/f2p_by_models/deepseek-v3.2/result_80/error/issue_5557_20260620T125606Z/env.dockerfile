FROM python:3.12-slim

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

WORKDIR /app

COPY . .

# Set PYTHONPATH to include common source directories
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages

RUN python -m pip install --upgrade pip setuptools wheel

# First, try to install dependencies from pyproject.toml if it exists
RUN if [ -f "pyproject.toml" ]; then \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi; \
fi

# Install the package in editable mode unconditionally
RUN pip install -e .

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai asyncpg

# Verify basic imports work
RUN python -c "import sys; print('Python path:', sys.path)" && \
    python -c "import pytest; print('Pytest version:', pytest.__version__)"

CMD ["/bin/bash"]