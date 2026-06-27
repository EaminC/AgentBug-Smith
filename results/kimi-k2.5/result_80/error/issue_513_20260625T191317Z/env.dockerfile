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

FROM python:3.9-slim

WORKDIR /app

# Copy repository contents
COPY . .

# Install system dependencies if needed for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Safe dependency installation - handle requirements.txt only if it exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Handle optional test requirements
RUN if [ -f requirements-test.txt ]; then pip install --no-cache-dir -r requirements-test.txt; fi
RUN if [ -f test-requirements.txt ]; then pip install --no-cache-dir -r test-requirements.txt; fi

# Editable installation of the package (unconditional as per requirements)
RUN pip install -e .

# Handle monorepo structure - check for common sub-package locations and install them
RUN if [ -d src ]; then pip install -e src; fi
RUN if [ -d libs/core ]; then pip install -e libs/core; fi
RUN if [ -d packages/agentscope ]; then pip install -e packages/agentscope; fi

# Set comprehensive PYTHONPATH to handle both standard and monorepo layouts
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages:/app/agentscope:$PYTHONPATH

# Install pytest explicitly to ensure test runner availability
RUN pip install --no-cache-dir pytest pytest-asyncio