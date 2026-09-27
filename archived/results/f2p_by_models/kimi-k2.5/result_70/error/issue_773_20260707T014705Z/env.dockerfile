FROM python:3.12-slim

# Set working directory
WORKDIR /app

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

# Install system dependencies including tkinter for gpt_engineer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        python3-tk \
        tk-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        libffi-dev \
        libssl-dev \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0"

# Copy the entire repository
COPY . .

# Install a compatible version of langchain that has MODEL_COST_PER_1K_TOKENS
# This constant was removed in langchain 0.1.x, so we need to stay in 0.0.x series
# Version 0.0.325 is known to have this attribute
RUN pip install --no-cache-dir "langchain>=0.0.240,<0.0.350"

# Install Python dependencies from requirements.txt if it exists
# But skip langchain as we already installed a specific version
RUN if [ -f "requirements.txt" ]; then \
        grep -v "^langchain" requirements.txt > /tmp/requirements_filtered.txt && \
        pip install --no-cache-dir -r /tmp/requirements_filtered.txt || \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Install project in editable mode
# This will install deps from pyproject.toml, but langchain is already installed
RUN pip install --no-cache-dir -e .

# Install test utilities that are compatible with pytest 7.3.1
# We must NOT upgrade pytest as gpt-engineer requires pytest==7.3.1
RUN pip install --no-cache-dir \
    pytest-mock==3.11.1 \
    pytest-asyncio==0.21.0 \
    pytest-cov==4.1.0 \
    pytest-timeout==2.1.0 \
    pytest-xdist==3.3.1

# Verify installation
RUN python -c "import sys; print(f'Python {sys.version}')" && \
    python -c "import pytest; print(f'pytest {pytest.__version__} available')" && \
    python -c "from langchain.callbacks.openai_info import MODEL_COST_PER_1K_TOKENS; print('langchain MODEL_COST_PER_1K_TOKENS import OK')" && \
    python -c "import gpt_engineer; print('gpt_engineer import OK')"

# Default command
CMD ["/bin/bash"]
