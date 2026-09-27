# branch: python/requirements.txt - optimized for AutoGPT with Forge API
FROM python:3.11-slim

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
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gcc \
    g++ \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN python -m pip install --upgrade pip \
    && pip install "setuptools==67.7.2" "wheel==0.40.0" "hatchling"

# Copy entire repository (excluding .dockerignore patterns)
COPY . .

# Create README.md for hatchling build (excluded by .dockerignore)
RUN echo "# Auto-GPT: An Autonomous GPT-4 Experiment" > README.md && \
    echo "" >> README.md && \
    echo "Auto-GPT is an experimental open-source application showcasing the capabilities of the GPT-4 language model." >> README.md && \
    echo "This program, driven by GPT-4, chains together LLM thoughts, to autonomously achieve whatever goal you set." >> README.md && \
    echo "As one of the first examples of GPT-4 running fully autonomously, Auto-GPT pushes the boundaries of what is possible with AI." >> README.md

# First install pinned versions of packages that have conflicts
# Install pydantic and typer versions compatible with spacy and openapi-python-client
RUN pip install "pydantic<1.11.0,>=1.7.4" "typer<0.8.0,>=0.3.0"

# Install httpx version compatible with openapi-python-client
RUN pip install "httpx<0.25.0,>=0.15.4"

# Install click version compatible with gtts
RUN pip install "click==8.1.8"

# Now install requirements.txt, filtering out packages we already installed
RUN if [ -f requirements.txt ]; then \
    grep -v "^pydantic" requirements.txt | \
    grep -v "^typer" | \
    grep -v "^httpx" | \
    grep -v "^click" | \
    grep -v "^spacy" | \
    grep -v "^en-core-web-sm" | \
    grep -v "^auto-gpt-plugin-template" > /tmp/filtered_requirements.txt && \
    pip install -r /tmp/filtered_requirements.txt; \
    fi

# Install spacy with compatible version
RUN pip install "spacy==3.5.0"

# Install spacy model
RUN pip install "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.5.0/en_core_web_sm-3.5.0-py3-none-any.whl"

# Install auto-gpt-plugin-template from git
RUN pip install "git+https://github.com/Significant-Gravitas/Auto-GPT-Plugin-Template@0.1.0"

# Install test utilities (do NOT install litellm or mem0ai which cause conflicts)
RUN pip install \
    pytest \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    vcrpy \
    pytest-benchmark \
    pytest-integration \
    pytest-recording \
    anyio

# Create symlink for project name 'agpt' pointing to 'autogpt' directory
RUN ln -sf /app/autogpt /app/agpt

# Install the package in development mode (editable install)
RUN pip install -e .

# Set PYTHONPATH to include the source code for imports
ENV PYTHONPATH=/app:/app/autogpt

# Reinstall numpy to fix binary compatibility issues with spacy/thinc
RUN pip install --force-reinstall "numpy<2.0"

# Verify core imports work
RUN python -c "import autogpt; print('✓ AutoGPT imported successfully')" \
    && python -c "import openai; print('✓ OpenAI imported')" \
    && python -c "import yaml; print(f'✓ PyYAML {yaml.__version__} imported')" \
    && python -c "import pytest; print(f'✓ pytest {pytest.__version__} imported')" \
    && python -c "import auto_gpt_plugin_template; print('✓ auto_gpt_plugin_template imported successfully')" \
    && python -c "print('✓ Core imports successful')"

# Verify Forge API environment variables are set
RUN python -c "import os; print('=== Forge API Configuration ==='); print(f'OPENAI_BASE_URL: {os.getenv(\"OPENAI_BASE_URL\")}'); print(f'OPENAI_API_KEY: [set]'); print(f'ANTHROPIC_BASE_URL: {os.getenv(\"ANTHROPIC_BASE_URL\")}'); print(f'ANTHROPIC_AUTH_TOKEN: [set]'); print('============================')"

# Verify environment is ready for standalone Python scripts
RUN python -c "import sys, os, json, requests; print('✓ Python environment ready for standalone scripts'); print(f'Python {sys.version.split()[0]} ready'); print(f'Working directory: {os.getcwd()}'); print(f'PYTHONPATH: {os.getenv(\"PYTHONPATH\")}')"

CMD ["/bin/bash"]