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
COPY . .
# Repository uses Poetry (pyproject.toml and poetry.lock implied by Makefile and CI).
# Must install dev dependencies (pytest is in dev group) and the package itself.
# Since there is a src/ layout (gpt_engineer/ inside root, not src/), we do editable install.
RUN python -m pip install --upgrade pip wheel && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --with dev && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai
# Preflight import check
RUN python -c 'import pkg_resources, pytest, gpt_engineer; print("preflight ok")'
CMD ["/bin/bash"]