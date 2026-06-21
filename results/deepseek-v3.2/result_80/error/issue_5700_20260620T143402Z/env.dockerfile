FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Set up environment variables required by Forge
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy the entire repository
COPY . .

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

# Install the package in editable mode (CRITICAL)
RUN pip install -e .

# Also install any requirements.txt if present
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi

# Check for multi-package layout and install sub-packages
RUN if [ -d "libs" ]; then \
    find libs -name "pyproject.toml" -o -name "setup.py" | while read f; do \
        dir=$(dirname "$f"); \
        echo "Installing package from $dir"; \
        pip install -e "$dir"; \
    done; \
    fi

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/libs:/app/src:$PYTHONPATH

# Verify installation
RUN python -c "import pytest; print('pytest available')"

CMD ["/bin/bash"]