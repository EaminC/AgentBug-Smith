FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set working directory
WORKDIR /app

# Copy entire repo into container
COPY . .

# Install system dependencies for building and running Python packages, including Rust for tiktoken build
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        libffi-dev \
        libssl-dev \
        python3-dev \
        curl \
        ca-certificates \
        rustc \
        cargo \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel and compatible setuptools version
RUN python -m pip install --upgrade pip setuptools==81.0.0 wheel

# Install Python dependencies and the package itself with test tools
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi

# Install local package in editable mode unconditionally
RUN pip install -e . pytest pytest-mock pytest-xdist pytest-timeout pytest-asyncio pytest-cov anyio litellm

# Sanity check for package imports
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set Forge environment variables to override OpenAI and Anthropic endpoints
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Set PYTHONPATH to include /app for proper imports
ENV PYTHONPATH=/app

# Entrypoint: open a bash shell for test harness
CMD ["/bin/bash"]

# branch: python with requirements.txt and Forge API environment configured