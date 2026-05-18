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

# Set environment variables for Forge API compatibility (OpenAI and Anthropic SDKs)
ENV FORGE_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies needed to build Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev python3-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt if it exists
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi

# Install local project in editable mode unconditionally
RUN pip install -e .

# Install test dependencies unconditionally
RUN pip install pytest pytest-mock pytest-xdist pytest-timeout pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pandas

# Add /app to PYTHONPATH for module imports resolving (fix errors importing local modules like 'valuecell' and 'a2a')
ENV PYTHONPATH=/app

# Preflight test to verify package imports, pytest loads, and installed modules
RUN python -c "import pkg_resources, pytest, pandas; print('preflight ok')"

# Default command to keep container interactive
CMD ["/bin/bash"]

# branch: python with requirements.txt install, editable install, Forge API env vars, test deps, PYTHONPATH fix