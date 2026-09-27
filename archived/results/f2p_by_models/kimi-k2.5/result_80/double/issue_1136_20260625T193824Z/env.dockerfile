FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy repository source code
COPY . .

# Install dependencies safely if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Unconditionally install the local project in editable mode
RUN pip install -e .

# Handle potential monorepo structures by checking common subdirectories
RUN if [ -f libs/agentscope/setup.py ] || [ -f libs/agentscope/pyproject.toml ]; then \
    pip install -e libs/agentscope; \
    fi

# Set PYTHONPATH to include potential source directories for monorepo support
ENV PYTHONPATH=/app:/app/src:/app/libs/agentscope:/app/libs:${PYTHONPATH}

# Preserve existing environment variables for API access
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

# Install pytest for test execution
RUN pip install pytest