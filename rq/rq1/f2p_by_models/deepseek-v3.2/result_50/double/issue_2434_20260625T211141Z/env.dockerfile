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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:$PYTHONPATH

# Install dependencies and project
RUN python -m pip install --upgrade pip wheel && \
    if [ -f uv.lock ]; then \
        uv pip install -r uv.lock; \
    elif [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    pip install -e .[tools,embeddings,agentops,fastembed,pdfplumber,pandas,openpyxl,mem0,docling,aisuite] && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout pytest-subprocess pytest-vcr "setuptools<=81.0.0" litellm anyio

# Install any sub-packages in editable mode
RUN find /app -name "setup.py" -o -name "pyproject.toml" | grep -E "(libs|packages|src)" | head -5 | while read f; do \
    dir=$(dirname "$f"); \
    echo "Installing editable package from $dir"; \
    cd "$dir" && pip install -e . || true; \
    cd /app; \
    done

# Preflight import check
RUN python -c "import crewai, pytest; print('preflight ok')"

CMD ["/bin/bash"]