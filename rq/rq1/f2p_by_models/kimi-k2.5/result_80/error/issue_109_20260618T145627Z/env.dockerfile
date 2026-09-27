FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository context
COPY . .

# Install requirements safely if they exist
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

# Handle multi-package layout: install main package and common sub-packages in editable mode
# AgentScope typically has src/agentscope or similar structure
RUN pip install -e . || true
RUN if [ -f src/agentscope/setup.py ] || [ -f src/agentscope/pyproject.toml ]; then pip install -e src/agentscope; fi
RUN if [ -f setup.py ] || [ -f pyproject.toml ]; then pip install -e .; fi

# Set PYTHONPATH to cover common monorepo layouts
ENV PYTHONPATH=/app/src:/app/agentscope:/app:${PYTHONPATH}

# Environment variables for API access (dynamic retrieval in tests will use these)
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
ENV DASHSCOPE_API_KEY="sk-fake-key-for-testing"

# Default command to run the test
CMD ["python", "-m", "pytest", "test_formatter_dashscope.py", "-v"]