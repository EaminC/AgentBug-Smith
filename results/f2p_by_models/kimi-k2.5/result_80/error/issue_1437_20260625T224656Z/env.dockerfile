FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install safely if they exist
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy the entire repository to /app
COPY . .

# Install the local project in editable mode (unconditional)
RUN pip install -e .

# Handle potential multi-package/monorepo layouts commonly found in agent frameworks
# Install subdirectories that contain package configurations
RUN if [ -f setup.py ] || [ -f pyproject.toml ]; then \
        pip install -e . 2>/dev/null || true; \
    fi

# If this is a monorepo with packages in src/ or specific dirs, ensure they're in path
# Common patterns: src/, packages/, libs/
RUN if [ -d src/agentscope ]; then \
        pip install -e src/ 2>/dev/null || true; \
    fi

# Explicitly set PYTHONPATH to cover common source layouts
ENV PYTHONPATH=/app:/app/src:/app/libs/agentscope:$PYTHONPATH

# Environment variables for API access (preserved from original injection)
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

# Default to running pytest on the tests directory
CMD ["python", "-m", "pytest", "tests/", "-v"]