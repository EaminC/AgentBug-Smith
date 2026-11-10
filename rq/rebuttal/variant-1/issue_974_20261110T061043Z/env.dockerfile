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

# Set workdir
WORKDIR /app

# Set Forge and Anthropic environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies needed to build Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repo to container
COPY . .

# Install Python dependencies if requirements.txt exists, then install project editable and test dependencies including moto
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout "setuptools<=81.0.0" litellm opentelemetry-sdk moto && \
    pip install -e .

# Set PYTHONPATH including src since repo uses src/ layout
ENV PYTHONPATH=/app:/app/src

# Preflight check
RUN python -c 'import pkg_resources, pytest, opentelemetry.sdk, moto; print("preflight ok")'

# Default command to go into bash
CMD ["/bin/bash"]