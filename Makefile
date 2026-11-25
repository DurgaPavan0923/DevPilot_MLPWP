.PHONY: help install test lint format typecheck clean docker-up docker-down docker-build ci cov smoke web-install web-check web-build web-dev run serve eval launch-check check-all

PYTHON ?= python

help:
	@echo "DevPilot Build & Automation Commands"
	@echo "  install      Install package and dependencies in editable mode"
	@echo "  lint         Run ruff linting and formatting check"
	@echo "  typecheck    Run strict mypy on backend and pnpm typecheck on web"
	@echo "  format       Auto-format codebase with ruff"
	@echo "  test         Run test suite with pytest"
	@echo "  cov          Run test suite with >=80% coverage check"
	@echo "  smoke        Run end-to-end agent harness smoke test"
	@echo "  launch-check Execute pre-flight launch readiness validation"
	@echo "  check-all    Run lint, typecheck, coverage tests, and launch check"
	@echo "  docker-build Build multi-stage API, Sandbox, and Web Docker images"
	@echo "  docker-up    Start full stack with Docker Compose"
	@echo "  docker-down  Stop Docker Compose stack"
	@echo "  web-install  Install web frontend dependencies via pnpm"
	@echo "  web-check    Run TypeScript, ESLint, and frontend tests"
	@echo "  web-build    Build Next.js web application"
	@echo "  web-dev      Start Next.js frontend in development mode"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev,full]"

lint:
	$(PYTHON) -m ruff check devpilot eval tests
	$(PYTHON) -m ruff format --check devpilot eval tests
	cd web && pnpm lint

typecheck:
	$(PYTHON) -m mypy --strict devpilot
	$(PYTHON) -m mypy --strict eval
	cd web && pnpm typecheck

format:
	$(PYTHON) -m ruff check --fix devpilot eval tests
	$(PYTHON) -m ruff format devpilot eval tests

test:
	$(PYTHON) -m pytest tests -v --durations=10

cov:
	$(PYTHON) -m pytest --cov=devpilot --cov-report=term-missing --cov-fail-under=80 tests/

smoke:
	$(PYTHON) scripts/smoke_test.py

launch-check:
	$(PYTHON) scripts/launch_check.py

ci: lint typecheck cov smoke web-check launch-check

check-all: ci

run:
	$(PYTHON) -m devpilot.cli run --task "Analyze repository health" --repo .

serve:
	$(PYTHON) -m devpilot.cli serve --host 0.0.0.0 --port 8000

eval:
	$(PYTHON) scripts/reproduce.py --allow-mock --concurrency 4

docker-build:
	docker build -t devpilot-api -f docker/Dockerfile.api .
	docker build -t devpilot-sandbox -f docker/Dockerfile.sandbox docker/
	docker build -t devpilot-web -f docker/Dockerfile.web web/

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

web-install:
	cd web && pnpm install --frozen-lockfile

web-check:
	cd web && pnpm typecheck && pnpm lint && pnpm test

web-build:
	cd web && pnpm build

web-dev:
	cd web && pnpm dev

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
