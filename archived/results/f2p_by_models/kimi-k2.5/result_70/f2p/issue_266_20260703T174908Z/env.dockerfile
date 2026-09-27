FROM python:3.12-slim

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

WORKDIR /app

# Set Forge API environment variables for OpenAI compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Set Forge API environment variables for Anthropic compatibility
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies for compilation (needed for packages like lxml, numpy, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Upgrade pip and install build dependencies
RUN python -m pip install --upgrade pip wheel setuptools

# Install project dependencies and additional packages needed for the project
# Note: The project dynamically imports anthropic and google.generativeai which
# are not in requirements.txt, so we install them explicitly
RUN if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi

# Install the project itself in editable mode
RUN pip install -e .

# Install additional packages that the project uses via dynamic imports
# but are not listed in requirements.txt
RUN pip install anthropic google-generativeai

# Install test dependencies (required for running tests)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio \
    "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Verify installation by checking key imports work
RUN python -c "import openai; print('openai ok')" && \
    python -c "import anthropic; print('anthropic ok')" && \
    python -c "import google.generativeai; print('google.generativeai ok')" && \
    python -c "import mle; print('mle ok')" && \
    python -c "import pytest; print('pytest ok')" && \
    echo "preflight ok"

CMD ["/bin/bash"]
