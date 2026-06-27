FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
# Fix: Use proper LiteLLM provider prefixes for environment variables
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/gpt-3.5-turbo"  # Changed to valid OpenAI model format
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="anthropic/claude-3-haiku"  # Changed to valid Anthropic format
ENV ANTHROPIC_SMALL_FAST_MODEL="anthropic/claude-3-haiku"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies for Python packages that require compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Preflight check for critical files
RUN [ -f pyproject.toml ] && echo "pyproject.toml found" || (echo "Missing pyproject.toml" && exit 1)

# Install dependencies based on evidence from repository (pyproject.toml exists, no requirements.txt)
# Repository uses uv for dev dependencies (from pyproject.toml tool.uv), but main dependencies are listed in pyproject.toml.
# The project uses hatchling as build-system.
# We'll install dependencies via pip (editable install) and include test dependencies explicitly.
RUN python -m pip install --upgrade pip wheel && \
    pip install -e . && \
    # Install test dependencies (including pytest, pytest-* packages, and setuptools<=81.0.0, litellm as required)
    # Added pytest-vcr for VCR cassette support
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai pytest-vcr

# Preflight import check
RUN python -c 'import crewai, pytest; print("preflight ok")'

CMD ["/bin/bash"]