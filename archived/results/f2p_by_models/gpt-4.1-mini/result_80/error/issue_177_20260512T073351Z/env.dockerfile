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

# Set working directory to the repository root
WORKDIR /app

# Copy entire repository into the container
COPY . .

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies required to build some Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies and the project itself in editable mode
# Install test dependencies including pytest and related plugins
RUN pip install hatchling \
    && pip install -e . \
    && pip install pytest pytest-cov pytest-asyncio pytest-mock pytest-xdist pytest-timeout pytest-snapshot anyio "setuptools<=81.0.0" litellm

# Set PYTHONPATH to enable imports from /app/python directory
ENV PYTHONPATH=/app/python

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY=forge-key

# Additional environment variables
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
ENV MODEL=tensorblock/gpt-4.1-mini
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV GITHUB_TOKEN=ghp_key
ENV TAVILY_API_KEY=tvly-key

# Default command to open a bash prompt
CMD ["/bin/bash"]