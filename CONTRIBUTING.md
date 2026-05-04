# Contributing to plane-pm-agent

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/kcbdev/plane-pm-agent.git
cd plane-pm-agent
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # then fill in your Plane dev instance details
python -m app
```

## Adding a New Tool

1. Add the tool function in `app/__init__.py` using the `@mcp.tool()` decorator.
2. Test it locally against your Plane instance.
3. If the tool handles structured output, document the return shape in `SPEC.md`.
4. Add a test case covering the happy path and error cases.
5. Run `ruff check . && pytest` — all tests must pass.

## Code Style

- Use `ruff check .` to lint (pre-commit hooks welcome).
- Keep functions short — extract helpers for repeated HTTP/API logic.
- All external API calls go through the `api_get`, `api_post`, `api_patch`, `api_delete` helpers.
- Type hints on all function signatures.
- Docstrings on every tool: describe every parameter and the return shape.

## Reporting Issues

Please include:
- Plane version (self-hosted / plane.so)
- Plane self-hosted commit/tag if self-hosted
- Full traceback or error message
- Steps to reproduce

## Pull Requests

- One tool per PR.
- Link the related Plane API documentation if you relied on it.
- Keep the `SPEC.md` in sync with any change to tool signatures or return shapes.