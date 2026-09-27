FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Set Python path to include the project root
ENV PYTHONPATH=/app/python:$PYTHONPATH

# Install Python dependencies
WORKDIR /app/python
RUN pip install --upgrade pip setuptools wheel

# Install project in editable mode
RUN pip install -e .

# Install test dependencies
RUN if [ -f "requirements-test.txt" ]; then \
        pip install -r requirements-test.txt; \
    elif [ -f "requirements-dev.txt" ]; then \
        pip install -r requirements-dev.txt; \
    else \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio; \
    fi

# Install any additional dependencies from pyproject.toml if present
RUN if [ -f "pyproject.toml" ]; then \
        pip install .[dev] || pip install .[test] || true; \
    fi

# Verify installation
RUN python -c "import valuecell; print('Import successful')"

# Default command - run tests
CMD ["pytest", "tests/", "-v"]