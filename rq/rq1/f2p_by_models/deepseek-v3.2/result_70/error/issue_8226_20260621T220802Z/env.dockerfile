FROM python:3.12-slim AS test_builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.cargo/bin/uv /usr/local/bin/uv

# Copy entire repository
COPY . .

# Install Python dependencies using uv
RUN uv sync --frozen --extra "postgresql"

# Install dev dependencies
RUN uv sync --frozen --group dev

# Install the project in editable mode
RUN uv pip install -e .

# Install additional dependencies
RUN uv pip install "setuptools<=81.0.0" litellm

# Set Python path
ENV PYTHONPATH=/app

# Preflight check
RUN python -c "import langflow; print('Langflow imported successfully')"

CMD ["/bin/bash"]