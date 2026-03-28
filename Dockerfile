FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files and source
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install git (required for uv to fetch git dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install dependencies (no dev extras)
RUN uv sync --frozen --no-dev

# Expose venv python so Nomad can run: python /workspace/entrypoint.py
ENV PATH="/app/.venv/bin:$PATH"

# Additional dependencies for backend executor
RUN uv pip install httpx 'input-gen @ git+https://github.com/edcraft-org/input-gen.git'

# Create non-root user
RUN useradd -m -u 10001 appuser

WORKDIR /workspace

USER appuser
