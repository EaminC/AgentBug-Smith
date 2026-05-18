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

# Set working directory
WORKDIR /app

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Explicitly set PYTHONPATH for multi-package repo layout (adjust paths if needed)
ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py:/app

# Copy entire repository into container
COPY . .

# Upgrade pip, setuptools, and wheel with pinned setuptools to avoid known issues
# Install dependencies using requirements.txt if present
# Then install the repo and sub-packages in editable mode unconditionally
# Pin langchain to a version known to have the missing modules to avoid import errors
# Finally install test dependencies and additional needed packages
RUN set -eux; \
    python -m pip install --upgrade pip setuptools==81.0.0 wheel; \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi; \
    pip install langchain==0.0.230; \
    pip install -e . -e libs/langgraph -e libs/prebuilt -e libs/sdk-py; \
    pip install pytest==7.3.1 pytest-mock pytest-xdist pytest-timeout pytest-asyncio pytest-cov anyio litellm

# Preflight import test to ensure langchain and other dependencies are installed correctly
RUN python -c 'import pytest; import litellm; import langchain; print("preflight ok")'

# Default command to open bash shell
CMD ["/bin/bash"]