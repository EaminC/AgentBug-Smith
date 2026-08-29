# CrewAI Python Environment with Forge API Configuration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" hatchling

# Copy the entire repository
COPY . .

# Install the crewai package with all dependencies
# Using --no-cache-dir to save space and handling src layout properly
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir \
    pytest>=8.0.0 \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pytest-timeout \
    pytest-vcr \
    pytest-subprocess \
    anyio \
    litellm \
    mem0ai \
    python-dotenv

# Clean pip cache and apt caches to reduce image size
RUN rm -rf /root/.cache/pip /tmp/* /var/tmp/* /var/lib/apt/lists/*

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set environment variables for Forge API (OpenAI-compatible)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Set Python path for proper imports (src layout - crewai is in /app/src/crewai)
ENV PYTHONPATH=/app/src

# Pre-flight check - verify crewai can be imported
RUN python -c "import crewai; print('crewai imported successfully')" && \
    python -c "import pytest; print('pytest imported successfully')"

# Default command - must be /bin/bash for testing environment
CMD ["/bin/bash"]
