FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tensorblock/gpt-4.1-mini" \
    AI_TEMPERATURE="0.7" \
    AI_MAX_TOKENS="1000" \
    AI_TOP_P="1" \
    AI_FREQUENCY_PENALTY="0" \
    AI_PRESENCE_PENALTY="0" \
    GITHUB_TOKEN="ghp_key" \
    TAVILY_API_KEY="tvly-key" \
    ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini" \
    ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini" \
    PYTHONPATH="/app"

WORKDIR /app

# Copy entire repository content
COPY . .

# Install system level dependencies for building common Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libffi-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies and project (with test dependencies)
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
  fi && \
  pip install -e . && \
  pip install pytest pytest-mock pytest-xdist pytest-timeout litellm "setuptools<=81.0.0"

# Preflight test imports
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

CMD ["/bin/bash"]