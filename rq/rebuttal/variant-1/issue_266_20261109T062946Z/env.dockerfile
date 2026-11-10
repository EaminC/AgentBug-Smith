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

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install system dependencies for building if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pytest to enable test execution
RUN pip install --no-cache-dir pytest

# Install local project in editable mode unconditionally
RUN pip install -e .

# If there are sub-packages, install them here (example commented out)
# RUN pip install -e libs/langgraph -e libs/prebuilt -e libs/sdk-py

# Set PYTHONPATH to include source directories if multi-package repo
# Adjust paths below as per actual repo structure
ENV PYTHONPATH=/app

# Default command to run tests (optional, can be overridden)
CMD ["pytest", "-v"]