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

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

# Copy entire repository
COPY . .

# Install system packages needed for building Python packages and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libffi-dev libssl-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel, and packaging
RUN python -m pip install --upgrade pip setuptools==81.0.0 wheel packaging

# Use requirements.txt if it exists to install dependencies, else fallback to pip install -e . only
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
fi

# Install the package itself in editable mode and required test dependencies
RUN pip install -e . \
    && pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout litellm "setuptools<=81.0.0"

# Set PYTHONPATH to include /app for local imports
ENV PYTHONPATH=/app

# Verify installation and pytest import
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]