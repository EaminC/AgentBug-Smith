FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Copy repository contents
COPY . .

# Upgrade pip and install dependencies
RUN python -m pip install --upgrade pip wheel setuptools

# Install openai<1.0 to match the old API used by this codebase
# The code uses openai.error.InvalidRequestError and openai.ChatCompletion.create()
# which are deprecated in openai>=1.0
RUN pip install "openai<1.0" typer

# Install project dependencies from requirements.txt if it exists
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout

# Set PYTHONPATH for module imports (project uses flat structure)
ENV PYTHONPATH=/app

# Verify installation - check openai.error exists (old API)
RUN python -c "import openai; print('openai version:', openai.__version__); print('has error module:', hasattr(openai, 'error')); print('preflight ok')"

CMD ["/bin/bash"]
