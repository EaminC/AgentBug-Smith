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

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Copy entire repository into the container
COPY . .

# Install system dependencies needed for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt if present, then install all local packages in editable mode
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi

# Detect sub-packages with setup.py or pyproject.toml and install them editable
# For this example, assume packages under /app/libs and /app/packages if exist
RUN set -eux; \
    if [ -d "libs" ]; then \
        for d in libs/*; do \
            if [ -f "$d/setup.py" ] || [ -f "$d/pyproject.toml" ]; then \
                pip install -e "$d"; \
            fi; \
        done; \
    fi; \
    if [ -d "packages" ]; then \
        for d in packages/*; do \
            if [ -f "$d/setup.py" ] || [ -f "$d/pyproject.toml" ]; then \
                pip install -e "$d"; \
            fi; \
        done; \
    fi; \
    # Always install root package editable
    pip install -e .

# Install test and utility dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-timeout anyio "setuptools<=81.0.0" litellm mem0ai

# Set PYTHONPATH to include all source directories for multi-package repo support
ENV PYTHONPATH=/app:/app/libs:/app/packages

# Preflight check for installed packages
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to enter a bash shell
CMD ["/bin/bash"]