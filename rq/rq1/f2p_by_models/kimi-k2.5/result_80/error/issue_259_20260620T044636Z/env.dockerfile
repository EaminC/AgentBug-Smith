FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the repository code
COPY . .

# Install requirements if they exist (safe operation)
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Handle potential monorepo structure: install all sub-packages in editable mode
# First try root package, then common subdirectories
RUN pip install -e . || true
RUN if [ -f setup.py ] || [ -f pyproject.toml ]; then pip install -e .; fi

# Handle monorepo layouts (libs/, packages/, src/)
RUN for dir in libs/* packages/* src/*; do \
    if [ -d "$dir" ] && ([ -f "$dir/setup.py" ] || [ -f "$dir/pyproject.toml" ]); then \
        pip install -e "$dir" || true; \
    fi \
    done

# Set PYTHONPATH to include potential source directories
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages:/app/agentscope

# Verify critical imports work
RUN python -c "from agentscope.formatter import DashScopeChatFormatter; print('DashScopeChatFormatter imported successfully')"

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