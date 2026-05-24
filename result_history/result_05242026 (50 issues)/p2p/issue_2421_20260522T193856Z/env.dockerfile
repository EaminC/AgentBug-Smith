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

WORKDIR /app

# Copy entire repository to container
COPY . .

RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies if requirements.txt exists, then install project and test dependencies
RUN set -eux; \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi; \
    pip install -e . pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm json_repair

# Preflight import check
RUN python -c 'import pkg_resources, pytest, json_repair; print("preflight ok")'

# Setup PYTHONPATH for src/ layout
ENV PYTHONPATH=/app/src

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY="forge-key"

# Final CMD to launch bash shell
CMD ["/bin/bash"]