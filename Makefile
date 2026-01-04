SHELL := /bin/bash
PYTHON := ./.venv/bin/python
PIP := $(PYTHON) -m pip
UVICORN := $(PYTHON) -m uvicorn
HOST ?= 127.0.0.1
PORT ?= 8000
REQUIREMENTS := requirements.txt
DEV_REQUIREMENTS := requirements-dev.txt
.DEFAULT_GOAL := help

.PHONY: help venv install install-dev run run-prod health test lint format clean nuke

help:
\t@printf "Available targets:\n"
\t@printf "  help        - show this message (default)\n"
\t@printf "  venv        - create or refresh the .venv directory\n"
\t@printf "  install     - install requirements.txt into .venv\n"
\t@printf "  install-dev - install requirements-dev.txt on top of install\n"
\t@printf "  run         - start uvicorn in development mode (--reload)\n"
\t@printf "  run-prod    - start uvicorn without reload\n"
\t@printf "  health      - curl http://$(HOST):$(PORT)/health\n"
\t@printf "  test        - run pytest if available\n"
\t@printf "  lint        - run ruff check if available\n"
\t@printf "  format      - run ruff format if available\n"
\t@printf "  clean       - remove caches\n"
\t@printf "  nuke        - remove caches and the virtualenv\n"

venv:
\t@if [ ! -d .venv ]; then python3 -m venv .venv; fi
\t@$(PIP) install --upgrade pip setuptools wheel >/dev/null

install: venv
\t@if [ -f "$(REQUIREMENTS)" ]; then \
\t\t$(PIP) install -r "$(REQUIREMENTS)"; \
\telse \
\t\techo "No $(REQUIREMENTS) file found, skipping install"; \
\tfi

install-dev: install
\t@if [ -f "$(DEV_REQUIREMENTS)" ]; then \
\t\t$(PIP) install -r "$(DEV_REQUIREMENTS)"; \
\telse \
\t\techo "No $(DEV_REQUIREMENTS) file found, skipping dev install"; \
\tfi

run: install
\t@$(UVICORN) app.main:app --host "$(HOST)" --port "$(PORT)" --reload

run-prod: install
\t@$(UVICORN) app.main:app --host "$(HOST)" --port "$(PORT)"

health:
\t@curl --fail "http://$(HOST):$(PORT)/health" >/dev/null && echo "health check passed" || echo "health check failed"

test: venv
\t@if $(PYTHON) -m pytest --version >/dev/null 2>&1; then \
\t\t$(PYTHON) -m pytest; \
\telse \
\t\techo "pytest not installed in $(PYTHON)" && exit 0; \
\tfi

lint: venv
\t@if $(PYTHON) -m ruff --version >/dev/null 2>&1; then \
\t\t$(PYTHON) -m ruff check .; \
\telse \
\t\techo "ruff not installed in $(PYTHON), skipping lint"; \
\tfi

format: venv
\t@if $(PYTHON) -m ruff --version >/dev/null 2>&1; then \
\t\t$(PYTHON) -m ruff format .; \
\telse \
\t\techo "ruff not installed in $(PYTHON), skipping format"; \
\tfi

clean:
\t@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
\t@rm -rf .pytest_cache .ruff_cache

nuke: clean
\t@rm -rf .venv
