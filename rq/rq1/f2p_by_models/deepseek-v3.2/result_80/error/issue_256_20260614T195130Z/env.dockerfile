FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository
COPY . .

# CRITICAL: Install project in editable mode unconditionally
RUN pip install -e .

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include /app for src/ layout detection
ENV PYTHONPATH=/app

# Preflight import check
RUN python -c 'import pytest; print("preflight ok")'

CMD ["/bin/bash"]

# Multi-stage build for minimal runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy only necessary files from test_builder
COPY --from=test_builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=test_builder /usr/local/bin /usr/local/bin

# Copy application source (excluding tests)
COPY src/ src/
COPY pyproject.toml .

# Install production dependencies only (no dev extras)
RUN if [ -f "requirements.txt" ]; then \
    pip install -r requirements.txt; \
    else \
    pip install .; \
    fi

# Set Forge environment variables (simplified - remove duplicates)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key

# Expose default FastAPI port
EXPOSE 8000

# Set the default command based on project scripts
CMD ["agentup", "--help"]