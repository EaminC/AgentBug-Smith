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

# Copy entire repository (critical for external test script injection)
COPY . .

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Install dependencies from pyproject.toml (no lockfile)
# The project's dependencies are listed in pyproject.toml under [project]dependencies
# We also install the project itself in editable mode, but note that tests may import via `gpt_engineer`
# and there is no `src/` layout; therefore `pip install -e .` is safe.
RUN pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to fail fast if core modules are missing
RUN python -c 'import pkg_resources, pytest; import gpt_engineer; print("preflight ok")'

# The CI workflow runs `pytest --cov=gpt_engineer`; we keep the same command for testing.
# The final CMD is inferred from the project's CLI entry point (gpt-engineer).
# According to pyproject.toml, the script is `gpt-engineer = 'gpt_engineer.main:app'`
# The entry point is a Typer app, so the default command should be the CLI.
# However, the Dockerfile is primarily for testing, so default to bash for interactive use.
CMD ["/bin/bash"]