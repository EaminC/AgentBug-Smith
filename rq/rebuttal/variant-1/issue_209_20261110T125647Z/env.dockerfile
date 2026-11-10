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

# Set working directory
WORKDIR /app

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    PYTHONPATH=/app

# Install system dependencies needed for building and running Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Provide fallback version for setuptools-scm to avoid build errors
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_DAPR_AGENTS=0.0.0

# Install dependencies, editable install, and required test packages (removed pytest-block-network)
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Preflight check to verify installation
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

# Default command to keep container open for running tests/scripts
CMD ["/bin/bash"]

# branch: python/pyproject.toml
