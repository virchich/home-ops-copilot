.PHONY: install check test test-unit test-integration eval eval-quick run ingest ingest-rebuild check-docs clean clean-reports frontend-install frontend-dev frontend-build docker-up docker-down docker-build help

# Default target
help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies with uv"
	@echo "  make check            - Run static analysis (ruff + mypy)"
	@echo "  make test             - Run all tests (unit + integration)"
	@echo "  make test-unit        - Run unit tests only (fast, no external deps)"
	@echo "  make test-integration - Run integration tests only (requires index)"
	@echo "  make eval             - Run evaluation on golden questions"
	@echo "  make eval-quick       - Run evaluation on 5 questions (quick test)"
	@echo "  make run              - Start FastAPI development server"
	@echo "  make ingest           - Run document ingestion (uses existing index if available)"
	@echo "  make ingest-rebuild   - Force rebuild the vector index from scratch"
	@echo "  make check-docs       - Check for PDFs missing from metadata.json"
	@echo "  make clean            - Remove cache files and build artifacts"
	@echo "  make clean-reports    - Remove eval report files"
	@echo "  make frontend-install - Install frontend dependencies"
	@echo "  make frontend-dev     - Start frontend development server"
	@echo "  make frontend-build   - Build frontend for production"
	@echo "  make docker-up        - Start backend + frontend with Docker Compose"
	@echo "  make docker-down      - Stop Docker Compose services"
	@echo "  make docker-build     - Rebuild Docker images"

# Install dependencies
install:
	uv sync

# Static analysis: lint, format, and type check
check:
	uv run ruff check --fix
	uv run ruff format
	uv run mypy .

# Run all tests (unit + integration)
test:
	uv run pytest

# Run unit tests only (fast, no external dependencies)
test-unit:
	uv run pytest -m "not integration"

# Run integration tests only (requires index to be built)
test-integration:
	uv run pytest -m integration

# Run full evaluation (50 questions)
eval:
	uv run python -m eval.run_eval

# Run quick evaluation (5 questions)
eval-quick:
	uv run python -m eval.run_eval --limit 5

# Start FastAPI development server
run:
	uv run uvicorn app.main:app --reload

# Run document ingestion (uses existing index if available)
ingest:
	uv run python -m app.rag.ingest

# Force rebuild the vector index from scratch
ingest-rebuild:
	uv run python -m app.rag.ingest --rebuild

# Check for PDFs missing from metadata.json
check-docs:
	@uv run python -m scripts.check_docs

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Clean up eval reports
clean-reports:
	rm -f eval/reports/*.json
	@echo "Eval reports cleared"

# Frontend: Install dependencies
frontend-install:
	cd frontend && npm install

# Frontend: Start development server
frontend-dev:
	cd frontend && npm run dev

# Frontend: Build for production
frontend-build:
	cd frontend && npm run build

# Docker: Start all services
docker-up:
	docker compose up -d

# Docker: Stop all services
docker-down:
	docker compose down

# Docker: Rebuild images
docker-build:
	docker compose build
