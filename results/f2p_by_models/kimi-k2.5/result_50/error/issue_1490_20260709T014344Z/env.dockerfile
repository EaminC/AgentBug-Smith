FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for compilation and general use
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, wheel, and setuptools (version constrained to avoid compatibility issues)
RUN pip install --upgrade pip wheel && \
    pip install "setuptools<=81.0.0"

# Copy the entire repository
COPY . .

# Install project dependencies and the project itself
# Using pip install -e . for pyproject.toml-based projects
RUN pip install -e .

# Install test dependencies explicitly
RUN pip install pytest pytest-mock pytest-asyncio pytest-forked pytest-timeout \
    fakeredis aiosqlite greenlet litellm mem0ai packaging

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

# Verify installation
RUN python -c "import agentscope; print('agentscope imported successfully')"

CMD ["/bin/bash"]
