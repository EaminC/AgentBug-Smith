FROM python:3.12-slim

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

# Install system dependencies including ffmpeg for pydub
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libffi-dev \
    libssl-dev \
    libasound2-dev \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*
    
# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel setuptools_scm

# Copy entire repository
COPY . .

# Install all dependencies in optimal order with proper quoting
RUN if [ -f "requirements.txt" ]; then \
    pip install --break-system-packages -r requirements.txt; \
    fi

RUN if [ -f "requirements/requirements-dev.txt" ]; then \
    pip install --break-system-packages -r requirements/requirements-dev.txt; \
    fi

# Install the project in editable mode
RUN pip install --break-system-packages -e .

# Install additional test dependencies
RUN pip install --break-system-packages \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    'setuptools<=81.0.0' \
    litellm \
    mem0ai || echo "Note: mem0ai package may not be available, continuing..."

# Additional AI configuration variables
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV PYTHONUNBUFFERED=1

# Set PYTHONPATH to include /app for proper imports
ENV PYTHONPATH=/app

# Preflight import check
RUN python -c "\
import sys; \
print('Python path:', sys.path); \
import pytest; \
print('pytest imported'); \
import litellm; \
print('litellm imported'); \
import pydub; \
print('pydub imported'); \
import aider; \
print('aider imported'); \
print('Preflight check: all required packages imported successfully')"

# Default command - bash shell for testing environment
CMD ["/bin/bash"]