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

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set PYTHONPATH explicitly for all source directories
ENV PYTHONPATH=/app/src:/app/libs:/app/packages:/app

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Install the project in editable mode unconditionally (CRITICAL)
RUN pip install -e .

# Install dependencies safely with conditionals
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi
RUN if [ -f "pyproject.toml" ]; then \
    pip install .[tools,embeddings,agentops,fastembed,pdfplumber,pandas,openpyxl,mem0,docling]; \
    fi

# Install test dependencies unconditionally
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout \
    "setuptools<=81.0.0" litellm anyio mem0ai

# Preflight check for core modules
RUN python -c "import crewai, pytest; print('preflight ok')"

CMD ["/bin/bash"]