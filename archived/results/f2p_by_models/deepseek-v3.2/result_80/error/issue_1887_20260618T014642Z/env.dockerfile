FROM python:3.11-slim

# Set environment variables for Forge API
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tuzi-deepseek-v3.2/deepseek-v3.2" \
    AI_TEMPERATURE="0.7" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    AI_MAX_TOKENS=1000 \
    AI_TOP_P=1 \
    AI_FREQUENCY_PENALTY=0 \
    AI_PRESENCE_PENALTY=0 \
    PIP_NO_CACHE_DIR=yes \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy entire repository
COPY . .

# Create and activate virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install system dependencies including additional build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    libyaml-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Install Cython and numpy first (required by many packages)
RUN pip install cython numpy

# Install requirements with specific handling for problematic packages
RUN if [ -f "requirements.txt" ]; then \
        # Create a temporary requirements file with fixes for problematic packages
        cp requirements.txt /tmp/requirements_fixed.txt; \
        # Replace pyyaml==6.0 with a newer version that has wheels
        sed -i 's/pyyaml==6.0/pyyaml>=6.0.1/' /tmp/requirements_fixed.txt; \
        # Try to install spacy from pre-built wheels first
        pip install "spacy>=3.0.0,<4.0.0" --only-binary :all: || pip install "spacy>=3.0.0,<4.0.0"; \
        # Install the rest of requirements
        pip install -r /tmp/requirements_fixed.txt; \
    else \
        echo "requirements.txt not found"; \
        exit 1; \
    fi

# CRITICAL: Install the project in development mode
RUN pip install -e .

# Install additional test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout \
    anyio litellm mem0ai

# Set PYTHONPATH for proper imports
ENV PYTHONPATH=/app

# Reinstall numpy to fix binary compatibility issues
RUN pip install --force-reinstall numpy

# Verify critical imports work (skip spacy due to version conflicts)
RUN python -c "import pytest; import autogpt; import distro; import yaml; import openai; print('preflight imports ok')"

# Default command (required for test harness)
CMD ["/bin/bash"]