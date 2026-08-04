# OpenCellComms engine Makefile
# Development and build automation

.PHONY: help install install-dev install-minimal test test-fast test-coverage lint format format-check clean clean-all build dev-setup ci-test check-release upload-test upload

# Default target
help:
	@echo "OpenCellComms Engine Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install          Install OpenCellComms in production mode"
	@echo "  install-dev      Install OpenCellComms with development dependencies"
	@echo "  install-minimal  Install only core dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-fast        Run fast tests only (skip slow/integration tests)"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting (flake8, mypy)"
	@echo "  format           Format code (black, isort)"
	@echo "  format-check     Check code formatting without changes"
	@echo ""
	@echo "Build and Distribution:"
	@echo "  build            Build distribution packages"
	@echo "  clean            Clean build artifacts"
	@echo "  clean-all        Clean all generated files"
	@echo ""

# Python and pip commands
PYTHON := python3
PIP := pip3

# Installation targets
install:
	$(PIP) install ".[diffusion,maboss]"

install-dev:
	$(PIP) install -e ".[dev,docs,jupyter,performance,visualization,diffusion,maboss]"
	@echo "Activating pre-commit hook (non-fatal)..."
	@cd .. && pre-commit install >/dev/null 2>&1 \
		&& echo "[OK] pre-commit hook installed (fast engine tests run on commit)" \
		|| echo "[!] pre-commit hook not installed - run 'pre-commit install' from the repo root"

install-minimal:
	$(PIP) install -e .

# Testing targets
test:
	pytest tests/ -v

test-fast:
	pytest tests/ -v -m "not slow and not integration"

test-coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

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

# Build targets
build:
	$(PYTHON) -m build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/

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
