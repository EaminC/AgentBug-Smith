FROM python:3.12-slim AS test_builder

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_MLE_AGENT="0.0.1.dev0"
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Set Python path for module imports
ENV PYTHONPATH=/app

# Install system dependencies required for building C++ extensions (chroma-hnswlib)
# and other compiled packages
# Critical: Install newer g++ compiler with full C++11 support and all build tools
# The chroma-hnswlib package requires C++11 standard library and compiler features
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    gcc \
    make \
    python3-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Upgrade pip, setuptools, and wheel with C++ optimization flags
RUN python -m pip install --upgrade pip setuptools wheel

# Set compiler flags to ensure C++11 support is properly enabled
# This is critical for chroma-hnswlib which requires modern C++ features
ENV CFLAGS="-std=c++11"
ENV CXXFLAGS="-std=c++11"
ENV LDFLAGS=""

# Install project dependencies from requirements.txt
# Use --no-cache-dir to avoid cache issues with large builds
# Combine requirements.txt installation with editable install in single RUN
RUN pip install --no-cache-dir -r requirements.txt && pip install -e .

# Install pytest and testing dependencies
RUN pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Verify installation
RUN python -c "import sys; print(f'Python {sys.version}'); import pytest; print('pytest available')"

CMD ["/bin/bash"]