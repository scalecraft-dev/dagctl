.PHONY: help clean build build-bytecode test-build upload-test install-test test lint

help: ## Show this help message
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf dagctl.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned"

build: clean ## Build bytecode-only wheel
	@echo "================================================"
	@echo "Building dagctl with bytecode-only distribution"
	@echo "================================================"
	@echo ""
	@echo "Building wheel with bytecode compilation..."
	python setup.py bdist_wheel
	@echo "  ✓ Built wheel"
	@echo ""

build-bytecode: build ## Alias for build
	@echo "Build complete!"

verify: ## Verify wheel contains only bytecode (no source files)
	@echo "Verifying source files removed..."
	@if [ ! -d "dist" ]; then echo "  ✗ No dist/ directory found. Run 'make build' first."; exit 1; fi
	@echo ""
	@echo "Wheel contents:"
	@echo "---------------"
	@unzip -l dist/*.whl | grep -E "dagctl/.*\\.pyc$$" || echo "  No .pyc files found"
	@echo ""
	@if unzip -l dist/*.whl | grep -E "dagctl/.*\\.py$$" | grep -v "__pycache__"; then \
		echo "  ⚠️  WARNING: .py source files found in wheel!"; \
		exit 1; \
	else \
		echo "  ✓ No source files found (only bytecode)"; \
	fi
	@echo ""

test-build: build verify ## Build and verify for test PyPI
	@echo "Build verified and ready for test PyPI upload"
	@echo ""
	@echo "Next step:"
	@echo "  make upload-test"

upload-test: ## Upload to Test PyPI
	@echo "Uploading to Test PyPI..."
	@if [ ! -d "dist" ]; then echo "  ✗ No dist/ directory found. Run 'make build' first."; exit 1; fi
	@echo ""
	@echo "Ensure you have configured ~/.pypirc with your Test PyPI token"
	@echo "See PUBLISHING.md for details"
	@echo ""
	@read -p "Press Enter to continue with upload to Test PyPI or Ctrl+C to cancel..."
	twine upload --repository testpypi dist/*
	@echo ""
	@echo "✓ Uploaded to Test PyPI"
	@echo ""
	@echo "Test installation:"
	@echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ dagctl"

upload-prod: ## Upload to production PyPI (use with caution)
	@echo "⚠️  WARNING: This will upload to PRODUCTION PyPI!"
	@echo ""
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" != "yes" ]; then \
		echo "Upload cancelled."; \
		exit 1; \
	fi
	@echo ""
	@echo "Uploading to PyPI..."
	twine upload dist/*
	@echo ""
	@echo "✓ Uploaded to PyPI"
	@echo "  pip install dagctl"

install-test: ## Install from Test PyPI
	pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ dagctl

install-dev: ## Install package in development mode
	pip install -e ".[dev]"

test: ## Run tests
	pytest tests/ -v --cov=dagctl --cov-report=term-missing

lint: ## Run linters
	ruff check dagctl/
	black --check dagctl/
	mypy dagctl/

format: ## Format code
	black dagctl/
	ruff check --fix dagctl/

# Complete workflow for test PyPI
release-test: clean build verify upload-test ## Complete release workflow for Test PyPI

# Show current version
version: ## Show current version
	@grep "^version" pyproject.toml | sed 's/version = "\(.*\)"/\1/'
