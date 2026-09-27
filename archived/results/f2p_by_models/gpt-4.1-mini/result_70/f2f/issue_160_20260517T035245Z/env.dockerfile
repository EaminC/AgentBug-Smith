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

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

COPY . .

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt if it exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install the local package in editable mode unconditionally
RUN pip install -e .

# Install test tooling and dependencies with setuptools capped version
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout anyio "setuptools<=81.0.0" litellm

# Set PYTHONPATH to include /app to ensure imports work correctly
ENV PYTHONPATH=/app

# Verify installation
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]