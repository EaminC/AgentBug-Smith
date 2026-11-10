FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter3/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set necessary environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Set working directory
WORKDIR /app

# Upgrade pip, setuptools and wheel for latest packaging support
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository to container
COPY . .

# Install Python dependencies safely and install project in editable mode unconditionally
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH to /app (no src/ directory found in repo root)
ENV PYTHONPATH=/app

# Preflight check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command for test harness
CMD ["/bin/bash"]