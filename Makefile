.PHONY: help install install-dev test test-unit test-integration lint format clean build publish

# Default target
help:
	@echo "Available commands:"
	@echo "  install       Install the package"
	@echo "  install-dev   Install the package with development dependencies"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code with black"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build the package"
	@echo "  publish       Publish to PyPI"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test,docs]"

# Testing
test:
	pytest

test-unit:
	pytest -m "not integration"

test-integration:
	pytest -m integration

# Code quality
lint:
	flake8 src tests
	mypy src
	black --check src tests

format:
	black src tests

# Build and publish
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*

# Development setup
setup-dev: install-dev
	pre-commit install