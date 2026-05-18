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

# Set working directory
WORKDIR /app

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Install system dependencies needed for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev python3-dev libxml2-dev libxslt1-dev libyaml-dev make \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Copy repository content
COPY . .

# Install dependencies robustly for requirements.txt
RUN if [ -f "requirements.txt" ]; then \
    pip install --upgrade setuptools; \
    pip install --no-cache-dir -r requirements.txt; \
    fi

# Install all relevant packages in editable mode unconditionally
RUN pip install --no-cache-dir -e . -e libs/langgraph -e libs/prebuilt -e libs/sdk-py

# Install test dependencies
RUN pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout

# Preflight check
RUN python -c 'import setuptools, pytest; print("preflight ok")'

# Default command
CMD ["/bin/bash"]