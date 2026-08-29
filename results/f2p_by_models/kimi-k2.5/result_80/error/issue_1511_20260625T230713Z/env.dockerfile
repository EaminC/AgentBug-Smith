FROM python:3.9-slim

WORKDIR /app

# Copy project files into the container
COPY . .

# Install system dependencies if needed for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies safely
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install the project in editable mode (CRITICAL for local imports to work)
RUN pip install -e .

# Set PYTHONPATH to ensure local packages are discoverable
ENV PYTHONPATH=/app:$PYTHONPATH

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

# Default command to run tests
CMD ["python", "-m", "pytest", "tests/formatter_dashscope_test.py", "-v"]