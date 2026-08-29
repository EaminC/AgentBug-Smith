FROM python:3.11-slim

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

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

COPY . .

RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel; \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi; \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# If the repo has sub-packages under libs/ or packages/, install them editable and set PYTHONPATH accordingly
# Detect sub-packages and install them editable if present
RUN set -eux; \
    if [ -d "libs" ]; then \
        for pkg in libs/*; do \
            if [ -f "$pkg/setup.py" ] || [ -f "$pkg/pyproject.toml" ]; then \
                pip install -e "$pkg"; \
            fi; \
        done; \
    fi; \
    if [ -d "packages" ]; then \
        for pkg in packages/*; do \
            if [ -f "$pkg/setup.py" ] || [ -f "$pkg/pyproject.toml" ]; then \
                pip install -e "$pkg"; \
            fi; \
        done; \
    fi

ENV PYTHONPATH=/app
RUN if [ -d "libs" ]; then \
        export PYTHONPATH=$PYTHONPATH:$(find libs -type d | tr '\n' ':'); \
    fi; \
    if [ -d "packages" ]; then \
        export PYTHONPATH=$PYTHONPATH:$(find packages -type d | tr '\n' ':'); \
    fi; \
    echo "PYTHONPATH=$PYTHONPATH"

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]