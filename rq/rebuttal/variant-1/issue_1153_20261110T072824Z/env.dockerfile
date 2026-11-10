# Use official Python 3.12 slim image as base
FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory inside container
WORKDIR /app

# Set environment variables for Forge API compatibility (OpenAI and Anthropic)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository contents to /app
COPY . .

# Install python dependencies if requirements.txt exists, then install the repo in editable mode, then install test dependencies (excluding pytest-block-network)
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH for correct imports
ENV PYTHONPATH=/app

# Default command to keep container open in bash shell
CMD ["/bin/bash"]

# branch: python/requirements.txt
