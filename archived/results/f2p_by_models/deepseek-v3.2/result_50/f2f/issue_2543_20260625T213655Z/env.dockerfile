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

# Install system dependencies commonly needed for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (mandatory for test injection)
COPY . .

# Configure PYTHONPATH for monorepo support
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:/app/agentscope:/app/crewai:$PYTHONPATH

# Upgrade pip and install build tools
RUN python -m pip install --upgrade pip wheel hatchling

# Install the local project in editable mode (CRITICAL)
RUN pip install -e .

# Install project dependencies from pyproject.toml if it exists
RUN if [ -f pyproject.toml ]; then \
        pip install -e .[tools,embeddings,mem0,fastembed,docling,aisuite,pandas,pdfplumber,openpyxl,agentops]; \
    else \
        echo "No pyproject.toml found"; exit 1; \
    fi

# Install dev dependencies
RUN pip install ruff mypy pre-commit mkdocs mkdocstrings mkdocstrings-python mkdocs-material mkdocs-material-extensions pillow cairosvg pytest pytest-vcr python-dotenv pytest-asyncio pytest-subprocess

# Mandatory test framework installation
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Install any requirements.txt files found
RUN find /app -name "requirements.txt" -type f | while read req; do \
        echo "Installing from $req"; \
        pip install -r "$req"; \
    done

# Install any requirements-dev.txt files found
RUN find /app -name "requirements-dev.txt" -type f | while read req; do \
        echo "Installing from $req"; \
        pip install -r "$req"; \
    done

# Preflight import check to verify core modules are accessible
RUN python -c "import crewai, pytest; print('preflight ok')"

# Default command (as required by test harness)
CMD ["/bin/bash"]