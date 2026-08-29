FROM python:3.11-slim AS test_builder

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

COPY . .

# Install dependencies
RUN python -m pip install --upgrade pip setuptools wheel

# Install project dependencies
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi

# Install the project in editable mode
RUN pip install -e .

# Install test dependencies including anthropic and pyyaml
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio \
    "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai \
    anthropic pyyaml openai

# Set Python path
ENV PYTHONPATH=/app

# Preflight check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]