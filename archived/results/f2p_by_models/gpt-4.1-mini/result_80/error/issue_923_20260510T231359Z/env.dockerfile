# Dockerfile for Python project configured to use Forge API instead of OpenAI API
# branch: python with requirements.txt, robust install, test deps

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

WORKDIR /app

# Copy entire repository to preserve injected scripts and project files
COPY . .

# Install system dependencies for building Python packages
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends gcc g++ libffi-dev libxml2-dev libxslt1-dev python3-dev; \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies, project, and test support packages
RUN set -eux; \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    else \
        echo "Warning: requirements.txt not found, skipping pip install"; \
    fi; \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Preflight validation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]