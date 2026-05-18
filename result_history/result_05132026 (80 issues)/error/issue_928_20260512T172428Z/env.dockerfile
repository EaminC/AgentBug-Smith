FROM python:3.11-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_rQ2mlz7LDlAGvQoJz3AQ6x4ZPuQH54AvSon"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set working directory
WORKDIR /app

# Set environment variables for Forge API (OpenAI and Anthropic API compatibility)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies needed for Python build and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel to stable versions
RUN python -m pip install --upgrade pip setuptools==81.0.0 wheel

# Copy entire repository into the container
COPY . .

# Install Python dependencies and package itself in editable mode using requirements.txt if present
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
fi && \
pip install -e . && \
pip install pytest pytest-mock pytest-xdist pytest-timeout pytest-asyncio pytest-cov anyio litellm setuptools<=81.0.0

# Set PYTHONPATH to include /app for local imports
ENV PYTHONPATH=/app

# Preflight check to verify installations
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Entrypoint: bash shell to facilitate testing and interactive use
CMD ["/bin/bash"]