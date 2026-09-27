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

# Set Forge API environment variables (ensure consistent URLs)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Set working directory
WORKDIR /app

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libffi-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Install dependencies and package
RUN if [ -f "requirements.txt" ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    elif [ -f "pyproject.toml" ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-root; \
    else \
        echo "No recognized Python dependency files found, skipping dependency installation."; \
    fi && \
    pip install -e . && \
    pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Preflight check
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

# Set PYTHONPATH for src/ layout to avoid import issues
ENV PYTHONPATH=/app/src

# Final command
CMD ["/bin/bash"]

# branch: python with pyproject.toml or requirements.txt, Forge API env vars, test deps, editable install