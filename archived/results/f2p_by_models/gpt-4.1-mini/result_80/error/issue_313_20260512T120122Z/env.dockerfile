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

# Set environment variables to configure Forge API URLs and keys for OpenAI and Anthropic compatibility
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tensorblock/gpt-4.1-mini" \
    AI_TEMPERATURE="0.7" \
    GITHUB_TOKEN="ghp_key" \
    TAVILY_API_KEY="tvly-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini" \
    ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini" \
    OPENAI_API_KEY="forge-key" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"

# Set working directory
WORKDIR /app

# Copy entire repository into container
COPY . .

# Install system dependencies needed for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libxml2-dev libxslt1-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies with fallback logic:
# - If requirements.txt exists, install dependencies from it
# - Then install the project in editable mode unconditionally
# - Finally, install explicit test dependencies required for pytest and related frameworks
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt ; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout anyio "setuptools<=81.0.0" litellm structlog uvicorn fastapi

# If the repo contains sub-packages, install them in editable mode here:
# Example (uncomment and adjust if needed):
# RUN pip install -e libs/langgraph -e libs/prebuilt -e libs/sdk-py

# Set PYTHONPATH for correct imports when running standalone scripts
ENV PYTHONPATH=/app

# Default command for container to open bash shell (required for test harness)
CMD ["/bin/bash"]