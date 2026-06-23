FROM node:20-slim

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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Check for package.json and install dependencies
RUN if [ -f package.json ]; then npm ci; fi

# Check for additional requirements files
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f pyproject.toml ]; then pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi; fi

# Install the project in development mode if it's a Python project
RUN if [ -f setup.py ] || [ -f pyproject.toml ]; then pip install -e .; fi

# Set PYTHONPATH for potential Python sub-packages
ENV PYTHONPATH=/app:/app/libs:/app/packages:/app/src

CMD ["/bin/bash"]