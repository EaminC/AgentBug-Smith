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

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip setuptools wheel

# Install vcrpy to fix ImportError for 'vcr' module in conftest.py
RUN pip install vcrpy

# Install requirements if requirements.txt exists
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi

# Install poetry and dependencies if poetry files exist
RUN if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi; \
    fi

# Install local project in editable mode unconditionally
RUN pip install -e .

# If multi-package layout detected, install sub-packages in editable mode
# (Adjust these paths if your repo has sub-packages)
RUN if [ -d "libs/langgraph" ]; then pip install -e libs/langgraph; fi
RUN if [ -d "libs/prebuilt" ]; then pip install -e libs/prebuilt; fi
RUN if [ -d "libs/sdk-py" ]; then pip install -e libs/sdk-py; fi

# Install test dependencies unconditionally
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai vcrpy

# Set PYTHONPATH to include main app and sub-packages for import resolution
ENV PYTHONPATH=/app:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]