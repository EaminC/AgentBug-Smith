FROM python:3.12-slim AS test_builder

# Install git for patch application
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

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

# Copy entire repo for test script injection
COPY . .

# Set PYTHONPATH for multi-package layout
ENV PYTHONPATH=/app:/app/src:/app/agentscope:$PYTHONPATH

# Upgrade pip and wheel, then install dependencies
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock setuptools<=81.0.0 litellm

# Preflight import check to fail fast if core modules are missing
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command for the container (used by test harness)
CMD ["/bin/bash"]