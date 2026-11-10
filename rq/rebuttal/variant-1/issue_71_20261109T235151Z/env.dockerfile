# branch: python/pyproject.toml

FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY=forge-key

# Set working directory
WORKDIR /app

# Copy full repository
COPY . .

# Upgrade pip, setuptools, and wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install dependencies from pyproject.toml and install editable package
# Install standard Python test dependencies excluding pytest-block-network
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH for src/ layout
ENV PYTHONPATH=/app:/app/src

# Default to bash shell for test harness
CMD ["/bin/bash"]
