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

# Copy the entire repository
COPY . .

# Set environment variables for Forge API compatibility (OpenAI-compatible endpoints)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY="forge-key" \
    PYTHONPATH=/app/mle:/app

# Upgrade pip and setuptools and wheel
# Install dependencies conditionally from requirements.txt
# Install the package itself editable
# Install required python test dependencies
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt; \
    fi && \
    pip install -e ./mle && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm && \
    python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]