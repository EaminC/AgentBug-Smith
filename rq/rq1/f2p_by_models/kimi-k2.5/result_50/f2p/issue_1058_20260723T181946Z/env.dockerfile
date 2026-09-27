FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-baseline/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-baseline/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-baseline/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies for SSL and build
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Update certificates
RUN update-ca-certificates

# Copy project files
COPY . .

# Configure pip for better reliability with SSL issues
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=10
ENV PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org"

# Install dependencies with multiple fallback strategies
RUN pip install --upgrade pip setuptools wheel --trusted-host pypi.org --trusted-host files.pythonhosted.org || \
    pip install --upgrade pip setuptools wheel --index-url http://pypi.python.org/simple --trusted-host pypi.python.org || \
    pip install --upgrade pip setuptools wheel

# Install project dependencies if requirements.txt exists
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org || \
        pip install -r requirements.txt --index-url http://pypi.python.org/simple --trusted-host pypi.python.org || \
        pip install -r requirements.txt; \
    fi

# Install project in editable mode
RUN pip install -e . --trusted-host pypi.org --trusted-host files.pythonhosted.org || \
    pip install -e . --index-url http://pypi.python.org/simple --trusted-host pypi.python.org || \
    pip install -e .

# Install test dependencies with multiple fallback strategies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout \
    --trusted-host pypi.org --trusted-host files.pythonhosted.org || \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout \
    --index-url http://pypi.python.org/simple --trusted-host pypi.python.org || \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout

# Set PYTHONPATH for the project
ENV PYTHONPATH=/app

# Verify installations
RUN python -c "import agentscope; print(f'agentscope version: {agentscope.__version__ if hasattr(agentscope, \"__version__\") else \"installed\"}')" && \
    python -c "import pytest; print(f'pytest version: {pytest.__version__}')"

CMD ["/bin/bash"]