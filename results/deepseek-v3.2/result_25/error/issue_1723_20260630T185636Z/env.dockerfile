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
COPY . .

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Set PYTHONPATH for multi-package layouts
# Check common directory structures and set PYTHONPATH accordingly
RUN if [ -d "libs" ]; then \
        find /app/libs -name "pyproject.toml" -o -name "setup.py" | head -5; \
    fi

# Install the main package in editable mode (CRITICAL)
RUN pip install -e .

# Install sub-packages if they exist (for multi-package layouts)
RUN if [ -d "libs" ]; then \
        find /app/libs -name "pyproject.toml" -o -name "setup.py" | while read f; do \
            dir=$(dirname "$f"); \
            echo "Installing $dir"; \
            pip install -e "$dir" || true; \
        done; \
    fi

# Install test dependencies
RUN if [ -f "requirements-test.txt" ]; then \
        pip install -r requirements-test.txt; \
    elif [ -f "requirements-dev.txt" ]; then \
        pip install -r requirements-dev.txt; \
    else \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout; \
    fi

# Preflight import check
RUN python -c "import crewai; print('crewai import ok')" || \
    python -c "print('crewai not found, checking for other packages'); import sys; print(sys.path)"

# Set default command
CMD ["/bin/bash"]