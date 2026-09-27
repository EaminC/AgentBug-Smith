FROM python:3.12-slim

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

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools early
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository
COPY . .

# Create virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install Poetry
RUN pip install poetry

# Configure Poetry to use the existing virtual environment
RUN poetry config virtualenvs.create false
RUN poetry config virtualenvs.in-project false

# Install dependencies with Poetry (include dev dependencies)
RUN poetry install --no-interaction --no-ansi

# Install the package in editable mode
RUN pip install -e .

# Install test dependencies explicitly
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout

# Install additional dependencies that might be needed
RUN pip install openai python-dotenv langchain langchain-openai langchain-anthropic pillow

# Set PYTHONPATH for imports
ENV PYTHONPATH="/app:$PYTHONPATH"

# Verify installation
RUN python -c "import sys; sys.path.insert(0, '.'); from gpt_engineer.core.default.steps import salvage_correct_hunks; print('SUCCESS: salvage_correct_hunks import works')"

CMD ["/bin/bash"]