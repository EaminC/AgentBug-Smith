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

# Set Forge API environment variables for OpenAI and Anthropic compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

# Always install the local project in editable mode
RUN pip install -e .

# Install dependencies conditionally
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    fi

# Install test dependencies unconditionally
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm

ENV PYTHONPATH=/app/src

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]

# branch: python project with requirements.txt preferred over poetry due to out-of-date lockfile, install dependencies with Forge API env vars configured