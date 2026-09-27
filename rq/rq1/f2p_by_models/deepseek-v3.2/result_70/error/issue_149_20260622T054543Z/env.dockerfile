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

# Copy the entire repository
COPY . .

# Check project structure
RUN echo "Project structure:" && find . -type f -name "*.py" | head -20 && \
    echo "Looking for Python packages..." && find . -type f -name "setup.py" -o -name "pyproject.toml" | head -10

# Set working directory to Python subproject if it exists
RUN if [ -d ./python ]; then \
        echo "Python project found in ./python" && \
        cd ./python && \
        echo "Contents of python directory:" && ls -la; \
    else \
        echo "No python subdirectory found, checking root for Python project" && \
        echo "Root contents:" && ls -la; \
    fi

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Determine project root and install dependencies
WORKDIR /app

# Check for Python project in various locations
RUN if [ -f ./python/pyproject.toml ] || [ -f ./python/setup.py ]; then \
        WORKDIR=/app/python && echo "Installing from ./python"; \
    elif [ -f ./pyproject.toml ] || [ -f ./setup.py ]; then \
        WORKDIR=/app && echo "Installing from root"; \
    else \
        echo "No Python project found" && exit 1; \
    fi

# Set the determined WORKDIR
WORKDIR $WORKDIR

# Install uv if uv.lock exists, else fallback to pip
RUN if [ -f uv.lock ]; then \
        echo "Installing uv..." && \
        curl -LsSf https://astral.sh/uv/install.sh | sh && \
        ~/.cargo/bin/uv pip install --system --no-cache-dir -e . && \
        ~/.cargo/bin/uv pip install --system --no-cache-dir \
            pytest \
            pytest-mock \
            pytest-asyncio \
            pytest-cov \
            anyio \
            "setuptools<=81.0.0" \
            litellm \
            pytest-xdist \
            pytest-timeout \
            mem0ai; \
    elif [ -f requirements.txt ]; then \
        echo "Installing via pip from requirements.txt..." && \
        python -m pip install --upgrade pip wheel && \
        pip install --no-cache-dir -r requirements.txt -e . && \
        pip install --no-cache-dir \
            pytest \
            pytest-mock \
            pytest-asyncio \
            pytest-cov \
            anyio \
            "setuptools<=81.0.0" \
            litellm \
            pytest-xdist \
            pytest-timeout \
            mem0ai; \
    elif [ -f pyproject.toml ]; then \
        echo "Installing via pip from pyproject.toml..." && \
        python -m pip install --upgrade pip wheel && \
        pip install --no-cache-dir -e . && \
        pip install --no-cache-dir \
            pytest \
            pytest-mock \
            pytest-asyncio \
            pytest-cov \
            anyio \
            "setuptools<=81.0.0" \
            litellm \
            pytest-xdist \
            pytest-timeout \
            mem0ai; \
    else \
        echo "No dependency file found" && exit 1; \
    fi

# Set PYTHONPATH to include current directory and parent
ENV PYTHONPATH=/app:/app/python:$PYTHONPATH

# Verify installation
RUN python -c "import sys; print('Python path:', sys.path)" && \
    python -c "import pkg_resources; print('Packages installed:', [pkg.key for pkg in pkg_resources.working_set][:10])"

# Create a simple test to verify the environment
RUN echo 'import os\nimport sys\nprint("Python version:", sys.version)\nprint("PYTHONPATH:", os.environ.get("PYTHONPATH", ""))\nprint("Test environment ready")' > /tmp/test_env.py && \
    python /tmp/test_env.py

# Default command: start shell for exploration
CMD ["/bin/bash"]