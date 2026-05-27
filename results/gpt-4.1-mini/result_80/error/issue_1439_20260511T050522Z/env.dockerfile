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

# Set environment variables for Forge API compatibility (deduplicated and corrected)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV FORGE_API_KEY="forge-key"

WORKDIR /app

# Copy entire repository into container
COPY . .

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    libffi-dev \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install poetry if pyproject.toml and poetry.lock exist
RUN if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
      python -m pip install poetry && \
      poetry config virtualenvs.create false && \
      poetry install --no-interaction --no-ansi ; \
    fi

# Install dependencies and repo itself unconditionally with editable install
RUN if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt ; \
    fi && \
    pip install -e .

# Ensure pytest, pytest-mock, pytest-asyncio, pytest-cov, anyio, setuptools<=81.0.0, litellm
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

# Preflight check to ensure imports work
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]

# branch: python with pyproject.toml and requirements.txt handling, Forge API env vars, unconditional editable install