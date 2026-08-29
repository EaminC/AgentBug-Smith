FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Install requirements safely if they exist
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install the package in editable mode (unconditional as per requirements)
RUN pip install -e .

# Handle potential monorepo structure - install subpackages if they exist
# AgentScope may have additional packages in src/ or similar
RUN if [ -f src/agentscope/requirements.txt ]; then pip install -r src/agentscope/requirements.txt; fi
RUN if [ -d src ]; then pip install -e src/agentscope 2>/dev/null || true; fi

# Set PYTHONPATH to include potential source directories for monorepo support
ENV PYTHONPATH=/app:/app/src:$PYTHONPATH

# --- AgentSmith inject .env from project root (dockerwrite) ---
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
# --- end inject ---

# Default command to run tests
CMD ["python", "-m", "pytest", "tests/formatter_dashscope_test.py", "-v"]