FROM python:3.12-slim

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

# Set working directory
WORKDIR /app

# Copy entire repo
COPY . .

# Upgrade pip, setuptools, wheel and install dependencies in one step
RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel; \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi; \
    pip install -e . pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm numpy ray

# Preflight check
RUN python -c 'import pkg_resources, pytest, numpy, ray; print("preflight ok")'

# Default to bash shell
CMD ["/bin/bash"]
