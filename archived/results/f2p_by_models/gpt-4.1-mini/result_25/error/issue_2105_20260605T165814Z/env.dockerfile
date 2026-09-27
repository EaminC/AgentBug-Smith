FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV GITHUB_TOKEN="ghp_key"
ENV HF_TOKEN="hf_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Set Forge environment variables (ensure consistent URLs)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Copy entire repository
COPY . .

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies unconditionally with editable install for local package
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Detect src/ layout or src imports and set PYTHONPATH accordingly
RUN if [ -d "src" ] || grep -Rq "^\s*from src\.|^\s*import src\." . ; then \
        echo "Detected src/ layout or src imports, setting PYTHONPATH"; \
        echo "export PYTHONPATH=/app" >> /etc/profile.d/pythonpath.sh; \
    fi

ENV PYTHONPATH=/app

# Preflight import check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Assumption: main.py is at src/my_project/main.py according to README and code examples
CMD ["python", "src/my_project/main.py"]