FROM python:3.12-slim

# Set environment variables to use Forge API instead of OpenAI API
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1 \
    MODEL=tensorblock/gpt-4.1-mini \
    AI_TEMPERATURE=0.7 \
    AI_MAX_TOKENS=1000 \
    AI_TOP_P=1 \
    AI_FREQUENCY_PENALTY=0 \
    AI_PRESENCE_PENALTY=0 \
    GITHUB_TOKEN=ghp_key \
    TAVILY_API_KEY=tvly-key

# Install system dependencies needed for building packages and Python headers
# Add g++ with at least C++11 support to build chroma-hnswlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# Upgrade pip, setuptools, wheel and install dependencies
# Install from requirements.txt if it exists, then install editable package
# Install testing dependencies explicitly with compatible setuptools version
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout numpy<2.0.0

# Preflight check to verify installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]