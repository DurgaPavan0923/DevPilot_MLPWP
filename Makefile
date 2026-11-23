.PHONY: help install test lint format clean docker-up docker-down

PYTHON ?= python
VENV_PYTHON = .venv/bin/python
ifeq ($(OS),Windows_NT)
    VENV_PYTHON = .venv\Scripts\python.exe
endif

help:
	@echo "DevPilot Build & Automation Commands"
	@echo "  install      Install dependencies into virtual environment"
	@echo "  test         Run test suite with pytest"
	@echo "  lint         Run ruff and mypy linters"
	@echo "  format       Format code with ruff"
	@echo "  clean        Clean build artifacts and cache"
	@echo "  docker-up    Start backend, web, and sandbox containers"
	@echo "  docker-down  Stop containers"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev,full]"

test:
	$(PYTHON) -m pytest tests -v --durations=10

lint:
	$(PYTHON) -m ruff check devpilot tests
	$(PYTHON) -m mypy devpilot tests

format:
	$(PYTHON) -m ruff format devpilot tests
	$(PYTHON) -m ruff check --fix devpilot tests

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
