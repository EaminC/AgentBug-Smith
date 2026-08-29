FROM python:3.9-slim

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository into the container
COPY . .

# Install requirements safely if they exist
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
RUN if [ -f test-requirements.txt ]; then pip install -r test-requirements.txt; fi

# Install the package in editable mode unconditionally
RUN pip install -e .

# Handle potential monorepo structure by checking common subpackage locations
RUN if [ -f packages/agentscope/setup.py ] || [ -f packages/agentscope/pyproject.toml ]; then \
        pip install -e packages/agentscope; \
    fi
RUN if [ -f src/setup.py ] || [ -f src/pyproject.toml ]; then \
        pip install -e src; \
    fi

# Set PYTHONPATH to include the app directory and potential source directories
ENV PYTHONPATH=/app:/app/src:/app/packages:$PYTHONPATH

# Environment variables for API configurations (preserved from original)
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

# Default command to run tests
CMD ["pytest", "tests/formatter_dashscope_test.py", "-v"]