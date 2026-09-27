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

# Set environment variables for Forge API compatibility with OpenAI and Anthropic SDKs
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

# Copy the entire repo into the container for build and tests
COPY . .

# Upgrade pip, setuptools, wheel before installing dependencies
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies conditionally
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt && pip install -e . && pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm; \
    elif [ -f "pyproject.toml" ]; then \
        pip install -e . && pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm; \
    else \
        pip install -e . && pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm; \
    fi

# Preflight check to confirm python and pytest import works
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Entrypoint is bash shell for test harness
CMD ["/bin/bash"]

# branch: python/pyproject.toml or requirements.txt
