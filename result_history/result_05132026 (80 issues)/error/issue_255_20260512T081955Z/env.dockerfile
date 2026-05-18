# branch: python/requirements.txt
FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository into container
COPY . .

# Install Python dependencies from requirements.txt if it exists and install the project in editable mode unconditionally
RUN if [ -f requirements.txt ]; then \
    pip install -r requirements.txt; \
fi && \
pip install -e . pytest pytest-mock pytest-xdist pytest-timeout pytest-snapshot anyio "setuptools<=81.0.0" litellm

# Set PYTHONPATH so standalone scripts can import modules from /app
ENV PYTHONPATH=/app

# Preflight: verify Python and pytest installed
RUN python -c "import pytest; print('preflight ok')"

# Default command to keep container shell open
CMD ["/bin/bash"]