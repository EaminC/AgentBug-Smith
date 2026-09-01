FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
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

# Install system dependencies if needed (based on evidence)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies based on repository evidence
# setup.py indicates install_requires=minimal_requires and extras_require
# The project uses src/ layout (src/agentscope). To avoid duplicate module loading,
# we install dependencies but NOT the project in editable mode. Instead we set PYTHONPATH.
RUN python -m pip install --upgrade pip wheel && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai && \
    # Install from setup.py's minimal_requires (core dependencies)
    pip install docstring_parser loguru==0.6.0 tiktoken Pillow requests chardet inputimeout openai>=1.3.0 numpy Flask==3.0.0 Flask-Cors==4.0.0 Flask-SocketIO==5.3.6 dashscope==1.14.1 ollama>=0.1.7 google-generativeai>=0.4.0 zhipuai

# Set PYTHONPATH to include src directory to allow imports without editable install
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Preflight import check
RUN python -c 'import agentscope, pytest; print("preflight ok")'

CMD ["/bin/bash"]