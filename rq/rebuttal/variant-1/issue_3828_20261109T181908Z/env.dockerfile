# env.dockerfile - Python project with Forge API configuration
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
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Install system dependencies needed to build and run Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository into container
COPY . .

# Upgrade pip and setuptools, then install dependencies and editable installs in one RUN step
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e ./lib/crewai -e ./lib/crewai-tools && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout pytest-asyncio pytest-cov pytest-vcr anyio "setuptools<=81.0.0" litellm

# Set PYTHONPATH environment variable for src/ layout packages to resolve imports during tests
ENV PYTHONPATH=/app/lib/crewai/src:/app/lib/crewai-tools/src

# Run a preflight check to confirm installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Final CMD to drop into bash shell
CMD ["/bin/bash"]