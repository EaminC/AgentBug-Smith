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
ENV MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
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

# Install system dependencies required for building Python packages
# Including additional libraries for onnxruntime, chromadb, and potential compilation needs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libgomp1 \
    libxml2-dev \
    libxslt1-dev \
    libc6-dev \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, wheel, and setuptools first to ensure proper package resolution
RUN python -m pip install --upgrade pip wheel setuptools

# Copy repository contents
COPY . .

# Install Python dependencies with error handling
# Install requirements first, then package in editable mode, then test dependencies
RUN pip install --no-cache-dir -r requirements.txt || \
    (echo "Retrying with pre-release versions..." && pip install --pre --no-cache-dir -r requirements.txt)

# Install the package in editable mode
RUN pip install --no-cache-dir -e .

# Install test dependencies separately for better error isolation
RUN pip install --no-cache-dir \
    pytest \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    anyio \
    "setuptools<=81.0.0" \
    litellm \
    mem0ai

# Pre-flight check - verify key imports work
RUN python -c "import pkg_resources, pytest; print('preflight ok')" && \
    python -c "import mle; print('mle package import ok')" && \
    python -c "import openai; print('openai package import ok')"

CMD ["/bin/bash"]