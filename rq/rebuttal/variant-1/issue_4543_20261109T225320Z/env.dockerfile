FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Install system dependencies for Python builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel and setuptools-scm
RUN python -m pip install --upgrade pip setuptools wheel setuptools-scm

# Copy entire repo including .git to ensure setuptools_scm can detect version
COPY . .

# Set Forge API environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Workaround for setuptools_scm failing to find version during docker build
# Provide a pretend version to avoid errors
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AIDER_CHAT=0.0.1

# Install Python dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    fi

# Install testing dependencies (removed pytest-block-network which is missing)
RUN pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Install editable package in repo root
RUN pip install -e .

# Set PYTHONPATH depending on presence of 'src/' directory
RUN if [ -d src ]; then \
      echo "Setting PYTHONPATH to /app:/app/src"; \
      echo "PYTHONPATH=/app:/app/src" > /etc/environment; \
    else \
      echo "Setting PYTHONPATH to /app"; \
      echo "PYTHONPATH=/app" > /etc/environment; \
    fi
ENV PYTHONPATH=/app

# Default command
CMD ["/bin/bash"]

# branch: python/requirements.txt
