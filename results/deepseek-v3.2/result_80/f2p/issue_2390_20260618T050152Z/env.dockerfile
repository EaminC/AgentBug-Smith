# branch: python/requirements.txt
FROM python:3.10-slim

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

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libssl-dev \
    libffi-dev \
    pkg-config \
    # For tiktoken compilation
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Rust via rustup for tiktoken compilation
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Upgrade pip and install setuptools early
RUN python -m pip install --upgrade pip wheel setuptools

# Copy entire repository
COPY . .

# Install pyyaml first with a compatible version
RUN pip install --break-system-packages "PyYAML>=5.3.1,<6.1"

# Install core dependencies from requirements.txt (excluding test dependencies)
# Follow the pattern from the main Dockerfile: strip test dependencies
RUN if [ -f "requirements.txt" ]; then \
        # Create a temporary requirements file without test dependencies
        sed '/Items below this point will not be included in the Docker Image/,$d' requirements.txt > /tmp/core_requirements.txt && \
        pip install --break-system-packages -r /tmp/core_requirements.txt; \
    fi

# Install spacy model from URL in requirements.txt
RUN if grep -q "en-core-web-sm" requirements.txt; then \
        # Extract URL from the @ syntax
        SPACY_URL=$(grep "en-core-web-sm" requirements.txt | sed -n 's/.*@ //p') && \
        if [ -n "$SPACY_URL" ]; then \
            pip install --break-system-packages "$SPACY_URL" || \
            echo "Warning: Could not install spacy model from URL: $SPACY_URL"; \
        else \
            python -m spacy download en_core_web_sm || \
            echo "Warning: Could not download spacy model"; \
        fi; \
    else \
        python -m spacy download en_core_web_sm || \
        echo "Warning: Could not download spacy model"; \
    fi

# Set PYTHONPATH to include the project directory
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Install test dependencies
RUN pip install --break-system-packages \
    pytest \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    anyio \
    litellm \
    mem0ai \
    asynctest \
    pytest-benchmark \
    pytest-integration \
    # Additional test dependencies that might be needed
    "httpx<0.25.0" \
    "pydantic<2.0.0" \
    "typer<0.8.0"

# Set Forge environment variables (redundant but ensures they're set)
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
ENV ANTHROPIC_MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV ANTHROPIC_SMALL_FAST_MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV TAVILY_API_KEY=tvly-dev-key
ENV GITHUB_TOKEN=ghp_key

# Preflight import check
RUN python -c 'import setuptools; import pytest; print("preflight ok")' && \
    python -c 'import autogpt; print("autogpt import ok")' && \
    python -c 'import tiktoken; print("tiktoken import ok")'

# Final command
CMD ["/bin/bash"]