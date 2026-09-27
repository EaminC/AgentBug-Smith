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

# Set environment variables for Forge API compatibility (OpenAI and Anthropic SDKs)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Set working directory
WORKDIR /app

# Copy entire repository into container
COPY . .

# Install system dependencies needed for building Python packages and git (required by setuptools_scm to detect version)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel early to ensure compatibility
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies from requirements.txt if it exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install the repository in editable mode and testing dependencies
RUN pip install -e . \
    && pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout

# Verify the installation is sane
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command: open a bash shell (required by test harness)
CMD ["/bin/bash"]

# branch: python/requirements.txt
