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

COPY . .

# Install dependencies including starlette and essential testing packages
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout && \
    pip install starlette uvicorn httpx

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["/bin/bash"]