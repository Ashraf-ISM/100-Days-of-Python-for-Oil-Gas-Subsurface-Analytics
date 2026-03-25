PYTHON ?= python

.PHONY: help setup test lint format clean

help:
	@echo "Available targets: setup, test, lint, format, clean"

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	pytest

lint:
	ruff check .

format:
	ruff format .
	black .

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__
