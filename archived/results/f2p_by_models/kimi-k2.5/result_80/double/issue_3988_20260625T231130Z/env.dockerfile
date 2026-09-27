FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the repository contents
COPY . .

# Install requirements safely if they exist
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements/dev.txt ]; then pip install -r requirements/dev.txt; fi

# Install the package in editable mode (unconditional)
RUN pip install -e .

# Handle potential monorepo structure - install sub-packages if they exist
RUN if [ -f src/setup.py ]; then pip install -e src/; fi
RUN if [ -f libs/agentscope/setup.py ]; then pip install -e libs/agentscope/; fi

# Set PYTHONPATH to include all possible source directories
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/libs/agentscope

# Environment variables for API configurations
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

# Verify installation
RUN python -c "import agentscope; print('AgentScope installed successfully')"