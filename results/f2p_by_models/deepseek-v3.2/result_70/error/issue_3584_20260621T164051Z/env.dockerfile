FROM node:20-slim AS test_builder

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

# Copy entire repository
COPY . .

# Update and install basic dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python Poetry if pyproject.toml exists
RUN if [ -f "pyproject.toml" ]; then \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry; \
    fi

# Install Node.js dependencies (primary for JavaScript repo)
RUN if [ -f "package.json" ]; then \
    npm ci --no-audit --no-fund; \
    fi

# Install frontend dependencies if separate package.json exists
RUN if [ -f "src/frontend/package.json" ]; then \
    cd src/frontend && npm ci --no-audit --no-fund; \
    fi

# Install Python dependencies if pyproject.toml exists
RUN if [ -f "pyproject.toml" ]; then \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --with dev; \
    fi

# Install the Python project in development mode if setup.py or pyproject.toml exists
RUN if [ -f "setup.py" ]; then \
    pip3 install -e .; \
    elif [ -f "pyproject.toml" ]; then \
    pip3 install -e .; \
    fi

# Install additional Python test dependencies if needed
RUN if [ -f "requirements-dev.txt" ]; then \
    pip3 install -r requirements-dev.txt; \
    elif [ -f "requirements.txt" ]; then \
    pip3 install -r requirements.txt; \
    fi

# Set PYTHONPATH for multi-package Python projects
ENV PYTHONPATH=/app:$PYTHONPATH

# Check for common Python package directories and add to PYTHONPATH
RUN if [ -d "libs" ]; then find /app/libs -type d -name "*.egg-info" -exec dirname {} \; | xargs -I {} echo {} >> /tmp/pythonpath.txt; fi && \
    if [ -d "packages" ]; then find /app/packages -type d -name "*.egg-info" -exec dirname {} \; | xargs -I {} echo {} >> /tmp/pythonpath.txt; fi && \
    if [ -f "/tmp/pythonpath.txt" ]; then \
        export ADDITIONAL_PATHS=$(cat /tmp/pythonpath.txt | tr '\n' ':' | sed 's/:$//') && \
        echo "PYTHONPATH=\$PYTHONPATH:\$ADDITIONAL_PATHS" >> ~/.bashrc; \
    fi

# Verify installations
RUN node --version && \
    npm --version && \
    python3 --version && \
    if command -v poetry > /dev/null 2>&1; then poetry --version; fi

CMD ["/bin/bash"]