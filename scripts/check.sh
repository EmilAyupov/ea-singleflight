#!/usr/bin/env bash

set -euo pipefail

# Переходим в корень проекта
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Ruff: lint ==="
uv run ruff check .

echo "=== Ruff: format ==="
uv run ruff format --check .

echo "=== Pyrefly ==="
uv run pyrefly check

echo "=== Pytest ==="
uv run pytest

echo "=== All checks passed! ==="
