# MicroC Makefile
# Development and build automation

.PHONY: help install install-dev test test-fast test-coverage lint format clean build docs serve-docs

# Default target
help:
	@echo "MicroC Development Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install          Install MicroC in production mode"
	@echo "  install-dev      Install MicroC in development mode with all dependencies"
	@echo "  install-minimal  Install only core dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-fast        Run fast tests only (skip slow/integration tests)"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting (flake8, mypy)"
	@echo "  format           Format code (black, isort)"
	@echo "  format-check     Check code formatting without changes"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Build documentation"
	@echo "  serve-docs       Serve documentation locally"
	@echo "  docs-clean       Clean documentation build"
	@echo ""
	@echo "Build and Distribution:"
	@echo "  build            Build distribution packages"
	@echo "  clean            Clean build artifacts"
	@echo "  clean-all        Clean all generated files"
	@echo ""
	@echo "Examples:"
	@echo "  run-example      Run example simulation"
	@echo "  run-tests        Run test simulation"

# Python and pip commands
PYTHON := python3
PIP := pip3

# Installation targets
install:
	$(PIP) install .

install-dev:
	$(PIP) install -e ".[dev,docs,jupyter,performance,visualization]"

install-minimal:
	$(PIP) install -e .

# Testing targets
test:
	pytest tests/ -v

test-fast:
	pytest tests/ -v -m "not slow"

test-coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

# Code quality targets
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

format-check:
	black --check src/ tests/
	isort --check-only src/ tests/

# Documentation targets
docs:
	cd docs && make html

serve-docs:
	cd docs/_build/html && $(PYTHON) -m http.server 8000

docs-clean:
	cd docs && make clean

# Build targets
build:
	$(PYTHON) -m build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean docs-clean
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/

# Example targets
run-example:
	$(PYTHON) run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml --steps 10

run-tests:
	$(PYTHON) run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml --steps 1

# Development workflow
dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify installation"

# CI/CD targets
ci-test: format-check lint test-coverage

# Release targets
check-release: clean build
	twine check dist/*

upload-test:
	twine upload --repository testpypi dist/*

upload:
	twine upload dist/*
