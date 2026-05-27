# Use official Python 3.12 slim image
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

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Working directory
WORKDIR /app

# Upgrade pip, setuptools and wheel early
RUN python -m pip install --upgrade pip setuptools wheel

# Install system packages needed for Python package builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libffi-dev \
    libssl-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy entire repository into container
COPY . .

# Install Python dependencies and local packages in editable mode unconditionally
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# If multi-package layout detected, install sub-packages editable and set PYTHONPATH accordingly
# (Example paths, adjust if actual sub-packages exist)
RUN if [ -d libs/langgraph ]; then pip install -e libs/langgraph; fi
RUN if [ -d libs/prebuilt ]; then pip install -e libs/prebuilt; fi
RUN if [ -d libs/sdk-py ]; then pip install -e libs/sdk-py; fi

ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Preflight check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to keep shell prompt
CMD ["/bin/bash"]