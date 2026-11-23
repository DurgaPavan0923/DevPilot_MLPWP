# Contributing to DevPilot

Thank you for contributing to DevPilot! As a research-focused coding agent harness, we emphasize code quality, security rigor, and empirical reproducibility.

## Development Workflow

1. **Python Environment**:
   - Python 3.11+ is required.
   - Install dependencies in editable mode:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # Or on Windows: .venv\Scripts\Activate.ps1
     pip install -e ".[dev,full]"
     ```

2. **Code Standards & Linting**:
   - Code must pass `ruff check` and `ruff format --check`.
   - All modules must satisfy `mypy --strict devpilot` without warnings or type ignores where possible.
   - Format with:
     ```bash
     ruff format devpilot eval tests
     ruff check --fix devpilot eval tests
     mypy --strict devpilot
     ```

3. **Testing**:
   - All tests must pass:
     ```bash
     pytest tests -q
     ```
   - Any bug fix or new feature must include corresponding regression or property tests.

4. **Security & Sandboxing**:
   - Always verify that file access goes through `PathSandbox`.
   - Shell commands must execute via validated `CommandPolicy`.
   - Never commit API keys or unredacted test fixtures.

5. **Pull Requests**:
   - Keep commits small, descriptive, and conventional (e.g., `feat:`, `fix:`, `test:`, `docs:`).
   - Ensure CI passes on all matrices before requesting review.
