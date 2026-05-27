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

# Set environment variables for Forge API compatibility (OpenAI and Anthropic SDKs)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key

# Install system dependencies required by Python packaging and building native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev python3-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository into container (includes src/, tests/, configs, etc.)
COPY . .

# Upgrade pip, setuptools, wheel first
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies using requirements.txt if it exists, then install project and test dependencies
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-timeout pytest-xdist anyio "setuptools<=81.0.0" litellm

# Set PYTHONPATH to include source directories for multi-package repo support
ENV PYTHONPATH=/app/src:/app/libs:/app/packages

# Verify installation with a simple preflight check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to keep the container open with bash prompt (required by test harness)
CMD ["/bin/bash"]