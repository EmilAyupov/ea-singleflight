uv init --lib singleflight
uv add --dev ruff pyrefly pytest pytest-asyncio
uv run pyrefly init
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run pytest
