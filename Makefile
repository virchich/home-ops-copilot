.PHONY: install check test eval run clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies with uv"
	@echo "  make check    - Run static analysis (ruff + mypy)"
	@echo "  make test     - Run tests with pytest"
	@echo "  make eval     - Run evaluation on golden questions"
	@echo "  make eval-quick - Run evaluation on 5 questions (quick test)"
	@echo "  make run      - Start FastAPI development server"
	@echo "  make clean    - Remove cache files and build artifacts"

# Install dependencies
install:
	uv sync

# Static analysis: lint, format, and type check
check:
	uv run ruff check --fix
	uv run ruff format
	uv run mypy .

# Run tests
test:
	uv run pytest

# Run full evaluation (50 questions)
eval:
	uv run python -m eval.run_eval

# Run quick evaluation (5 questions)
eval-quick:
	uv run python -m eval.run_eval --limit 5

# Start FastAPI development server
run:
	uv run uvicorn app.main:app --reload

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
