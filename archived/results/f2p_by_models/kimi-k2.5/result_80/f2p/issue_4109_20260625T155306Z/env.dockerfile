FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
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

# Install system dependencies evidenced by repository workflows and requirements
# libportaudio2: required for sounddevice (evidenced in ubuntu-tests.yml and requirements.txt)
# libsndfile1: required for soundfile (evidenced in requirements.txt)
# git: required for gitpython integration (evidenced in requirements.txt)
# gcc: build support for potential compilation of binary packages
RUN apt-get update && apt-get install -y \
    git \
    libportaudio2 \
    libsndfile1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entire repository to ensure injected test scripts are preserved
COPY . .

# Install dependencies: requirements.txt exists at repository root
# Project uses setuptools with package 'aider' at root (not src layout per pyproject.toml)
# Install mandatory testing frameworks per CRITICAL INSTRUCTIONS
RUN python -m pip install --upgrade pip wheel && \
    pip install -r requirements.txt && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight verification to fail fast on missing core modules
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]