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
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV TAVILY_API_KEY=tvly-dev-key
ENV GITHUB_TOKEN=ghp_key

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