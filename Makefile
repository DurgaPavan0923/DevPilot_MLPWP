.PHONY: help install test lint format clean docker-up docker-down docker-build ci cov smoke web-install web-check web-build

PYTHON ?= python

help:
	@echo "DevPilot Build & Automation Commands"
	@echo "  install      Install package and dependencies in editable mode"
	@echo "  lint         Run ruff and strict mypy quality gates"
	@echo "  format       Auto-format codebase with ruff"
	@echo "  test         Run test suite with pytest"
	@echo "  cov          Run test suite with >=80% coverage check"
	@echo "  smoke        Run end-to-end agent harness smoke test"
	@echo "  ci           Run full local continuous integration pass"
	@echo "  docker-build Build multi-stage API, Sandbox, and Web Docker images"
	@echo "  docker-up    Start full stack with Docker Compose"
	@echo "  docker-down  Stop Docker Compose stack"
	@echo "  web-install  Install web frontend dependencies via pnpm"
	@echo "  web-check    Run TypeScript, ESLint, and frontend tests"
	@echo "  web-build    Build Next.js web application"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev,full]"

lint:
	$(PYTHON) -m ruff check devpilot eval tests
	$(PYTHON) -m ruff format --check devpilot eval tests
	$(PYTHON) -m mypy --strict devpilot

format:
	$(PYTHON) -m ruff check --fix devpilot eval tests
	$(PYTHON) -m ruff format devpilot eval tests

test:
	$(PYTHON) -m pytest tests -v --durations=10

cov:
	$(PYTHON) -m pytest --cov=devpilot --cov-report=term-missing --cov-fail-under=80 tests/

smoke:
	$(PYTHON) scripts/smoke_test.py

ci: lint cov smoke web-check

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

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
