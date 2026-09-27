FROM python:3.12-slim

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

# Set critical environment variables
ENV PYTHONPATH=/app:/app/src:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel uv

# Copy entire repository
COPY . .

# Install project in editable mode unconditionally
RUN if [ -f "pyproject.toml" ]; then \
    uv pip install -e .[tools]; \
    elif [ -f "setup.py" ]; then \
    uv pip install -e .; \
    elif [ -f "requirements.txt" ]; then \
    uv pip install -r requirements.txt; \
    fi

# Install test dependencies
RUN uv pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Check for and install sub-packages if they exist
RUN if [ -d "libs" ]; then \
    find /app/libs -name "pyproject.toml" -o -name "setup.py" | while read f; do \
        dir=$(dirname "$f"); \
        echo "Installing sub-package from $dir"; \
        cd "$dir" && uv pip install -e . && cd /app; \
    done; \
    fi

# Update PYTHONPATH for any discovered packages
RUN if [ -d "libs" ]; then \
    find /app/libs -type d -name "*.egg-info" -o -type f -name "__init__.py" | \
    xargs -I {} dirname {} | sort -u | \
    while read dir; do \
        if [ -f "$dir/__init__.py" ] || [ -f "$dir/pyproject.toml" ] || [ -f "$dir/setup.py" ]; then \
            echo "Adding $dir to PYTHONPATH"; \
            export PYTHONPATH="$dir:$PYTHONPATH"; \
        fi; \
    done; \
    echo "export PYTHONPATH=\"$PYTHONPATH\"" >> /root/.bashrc; \
    fi

# Preflight import check
RUN python -c "import sys; print('Python path:', sys.path); print('PYTHONPATH:', sys.executable)"

CMD ["/bin/bash"]