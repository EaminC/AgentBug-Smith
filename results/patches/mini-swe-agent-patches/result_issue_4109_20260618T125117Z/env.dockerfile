FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AIDER_CHAT="0.0.1.dev0"
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="anthropic_base_url"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# branch: python/requirements.txt
WORKDIR /app

# Install system dependencies including git for setuptools_scm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Set Forge environment variables (required)
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0

# Set version for setuptools_scm to avoid git dependency during build
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AIDER_CHAT=1.0.0

# Copy entire repository (critical for external test injection)
COPY . .

# Install dependencies and project
# First install requirements.txt if it exists, then install project
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
fi

# Install testing dependencies unconditionally
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Install project in development mode
RUN pip install -e .

# Set environment variable for tests (from .github/workflows/ubuntu-tests.yml)
ENV AIDER_ANALYTICS=false
ENV AIDER_CHECK_UPDATE=false

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set PYTHONPATH to ensure imports work correctly
ENV PYTHONPATH=/app

# Final CMD for test harness
CMD ["/bin/bash"]

# Install mini-swe-agent and set configuration flag
RUN pip install --no-cache-dir mini-swe-agent && \
    mkdir -p /root/.config/mini-swe-agent && \
    echo "MSWEA_CONFIGURED=true" > /root/.config/mini-swe-agent/.env
