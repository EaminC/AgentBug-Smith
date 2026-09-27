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

# Set working directory to the root of the repository
WORKDIR /app

# Copy entire repository into container
COPY . .

# Set environment variables for Forge API compatibility with OpenAI and Anthropic SDKs
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    FORGE_API_KEY="forge-key"

# If the repo has multiple packages under libs/, install them all editable and set PYTHONPATH accordingly
# Adjust these paths if your repo structure differs
RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel; \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    elif [ -f poetry.lock ]; then \
        pip install poetry; \
        poetry config virtualenvs.create false; \
        poetry install --no-dev --no-interaction --no-ansi; \
    elif [ -f pyproject.toml ]; then \
        pip install -e .; \
    else \
        echo "No Python dependency files found, skipping install."; \
    fi; \
    # Install local project editable unconditionally to ensure local packages are available \
    pip install -e .; \
    # If libs/ contains sub-packages, install them editable as well (adjust as needed) \
    if [ -d libs/langgraph ]; then pip install -e libs/langgraph; fi; \
    if [ -d libs/prebuilt ]; then pip install -e libs/prebuilt; fi; \
    if [ -d libs/sdk-py ]; then pip install -e libs/sdk-py; fi; \
    pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm; \
    python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set PYTHONPATH to include all relevant source directories for multi-package repo
ENV PYTHONPATH=/app:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

CMD ["/bin/bash"]

# branch: python/requirements.txt or poetry-based with Forge API env vars set