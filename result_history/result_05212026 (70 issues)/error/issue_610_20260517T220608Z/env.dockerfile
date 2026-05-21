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

# Set working directory
WORKDIR /app

# Copy entire repository to container
COPY . .

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

# Set PYTHONPATH to include all relevant source directories (adjust as per repo structure)
ENV PYTHONPATH="/app:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py"

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies and the repository itself
RUN if [ -f "requirements.txt" ]; then \
      pip install --use-pep517 --no-cache-dir -r requirements.txt; \
    elif [ -f "pyproject.toml" ]; then \
      pip install poetry && \
      poetry config virtualenvs.create false && \
      poetry install --no-root --no-interaction --no-ansi; \
    else \
      echo "No recognized Python dependency files found, skipping installation."; \
    fi

# Install all local packages in editable mode unconditionally (adjust paths if needed)
RUN pip install -e . -e libs/langgraph -e libs/prebuilt -e libs/sdk-py

# Install obligatory Python test dependencies
RUN pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout setuptools<=81.0.0 litellm

# Verify Python and pytest imports
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to open bash shell inside container
CMD ["/bin/bash"]

# branch: python with Forge API environment, compatible with pyproject.toml and requirements.txt