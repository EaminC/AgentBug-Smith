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

# Install git and build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy repository
COPY . .

# Upgrade pip and install package with test dependencies
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov litellm "setuptools<=81.0.0"

ENV PYTHONPATH="/app:$PYTHONPATH"

# Preflight check
RUN python -c 'import interpreter, pytest; print("preflight ok")'

CMD ["/bin/bash"]