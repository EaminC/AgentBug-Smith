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

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Copy the entire repository into the container
COPY . .

# Install dependencies and the project itself
# Use requirements.txt if present; else fallback to poetry if lockfile present; else editable install
# Then install standard test dependencies separately with correct setuptools version specifier
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt ; \
    fi && \
    if [ -f pyproject.toml ] && [ -f poetry.lock ]; then \
      pip install poetry && poetry install ; \
    fi && \
    # Always install the local project in editable mode (including sub-packages if any)
    pip install -e . && \
    # If there are sub-packages, install them editable as well (adjust paths if needed)
    if [ -d libs/langgraph ]; then pip install -e libs/langgraph; fi && \
    if [ -d libs/prebuilt ]; then pip install -e libs/prebuilt; fi && \
    if [ -d libs/sdk-py ]; then pip install -e libs/sdk-py; fi && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH to include main app and sub-packages for import resolution
ENV PYTHONPATH=/app:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Preflight check
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

# Default cmd to bash for test harness compatibility
CMD ["/bin/bash"]

# branch: python/requirements.txt or pyproject.toml