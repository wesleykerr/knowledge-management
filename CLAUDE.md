# Claude Instructions

## Running Python Commands

Always use `uv run` to execute Python commands in this repository. Never use `python`, `python3`, or `python -m` directly.

```bash
# Tests
uv run pytest

# Scripts
uv run python knowledge/listener.py
```
