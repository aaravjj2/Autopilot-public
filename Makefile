# =============================================================================
# APEX Autopilot — Makefile
# =============================================================================
# Targets:  test lint typecheck coverage format clean dev-deps run help
# =============================================================================

SHELL := /bin/bash
PYTHON := python3
APP    := apex
WATCHLIST := tests/ -v --tb=short

.PHONY: help test lint typecheck coverage format clean dev-deps run run-scheduler run-autopilot run-dashboard run-health run-self-improvement run-gates docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Development workflow ----------------------------------------------------

dev-deps: ## Install all dev dependencies (pytest-cov, mypy, ruff, pre-commit)
	$(PYTHON) -m pip install --quiet pytest-cov mypy ruff pre-commit
	pre-commit install

test: ## Run all unit tests (fast)
	$(PYTHON) -m pytest $(WATCHLIST)

test-full: ## Run all tests (allows slow/smoke markers)
	$(PYTHON) -m pytest tests/ -v --tb=short

coverage: ## Run tests with coverage report
	$(PYTHON) -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --tb=short -q
	@echo "HTML report: htmlcov/index.html"

lint: ## Run ruff linter + format check
	ruff check src/
	ruff format --check src/

lint-fix: ## Auto-fix all lint issues + format
	ruff check --fix src/
	ruff format src/

typecheck: ## Run mypy type checker
	mypy src/ --ignore-missing-imports

format: ## Alias for lint-fix
	ruff check --fix src/
	ruff format src/

clean: ## Remove cache, coverage, and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov/ __pycache__/
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# --- Run targets -------------------------------------------------------------

run: ## Run one daily cycle (paper mode)
	$(PYTHON) -m apex.main

run-scheduler: ## Start the APScheduler blocking loop
	$(PYTHON) -m apex.main run-scheduler

run-autopilot: ## Start continuous autopilot (same as run-scheduler)
	$(PYTHON) -m apex.main run-autopilot

run-dashboard: ## Launch Streamlit UI
	streamlit run src/apex/dashboard/app.py --server.address 0.0.0.0

run-health: ## Start health check HTTP server
	$(PYTHON) -m apex.main run-health

run-self-improvement: ## Run one self-improvement cycle
	$(PYTHON) -m apex.main run-self-improvement

run-gates: ## Run predeployment gates
	$(PYTHON) -m apex.main run-gates

# --- Docker ------------------------------------------------------------------

docker-up: ## Start all containers
	docker compose up --build -d

docker-down: ## Stop all containers
	docker compose down

docker-logs: ## Follow all container logs
	docker compose logs -f

# --- Database ----------------------------------------------------------------

db-backup: ## Trigger a manual database backup
	$(PYTHON) backup_db.py

db-migrate: ## Run database migration
	$(PYTHON) migrate_consolidate_db.py

# --- Misc --------------------------------------------------------------------

version: ## Show Python + project info
	@$(PYTHON) --version
	@$(PYTHON) -c "import apex; print('apex:', getattr(apex, '__version__', 'no __version__'))" 2>/dev/null || true
	@grep '^version' pyproject.toml

git-hooks: ## Set up pre-commit hooks
	pre-commit install --install-hooks
