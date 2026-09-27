FROM python:3.12-slim

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
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"



# --- end inject ---

WORKDIR /app

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
ENV MODEL="openai/tuzi-gpt-4.1-mini/gpt-4.1-mini"

# Install system build dependencies for compiled Python packages
# onnxruntime requires g++, gcc, cmake, and libgomp1 (OpenMP)
# pandas and numpy require build-essential
# git is required for GitPython
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    build-essential \
    cmake \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and wheel, and install setuptools with proper version
RUN python -m pip install --upgrade pip wheel "setuptools<=81.0.0"

# Copy repository contents
COPY . .

# Install Python dependencies
# First install requirements.txt (includes openai~=1.34.0 and compatible jiter)
# Then install the package in editable mode
# Also install test dependencies and google-generativeai for Gemini support
# Note: Do NOT install litellm as it has conflicting dependencies with instructor (requires openai<2.0.0)
RUN pip install -r requirements.txt && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout google-generativeai

# Preflight check to verify Python environment is correctly set up
# Check that setuptools/pkg_resources is available and pytest works
RUN python -c 'import setuptools, pytest; print("preflight ok")'

# Default command to enter bash shell
CMD ["/bin/bash"]