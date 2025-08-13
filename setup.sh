#!/bin/bash

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create virtual environment and install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

echo "Project setup complete!"
