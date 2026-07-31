DIR := $(shell pwd)
BACKEND := $(DIR)/backend
FRONTEND := $(DIR)/frontend
VENV := $(BACKEND)/venv/bin
PY := $(VENV)/python
PIP := $(VENV)/pip

.PHONY: help setup dev status stop restart verify logs logs-fe \
        test test-backend test-frontend test-fast test-e2e \
        lint lint-fix db-init db-migrate

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Bootstrap dev environment (Postgres, Redis, deps, config)
	bash scripts/setup_dev.sh

dev: ## Start all dev services
	bash scripts/dev.sh start

status: ## Show service status + health
	bash scripts/dev.sh status

stop: ## Stop backend + frontend (Postgres container stays up)
	bash scripts/dev.sh stop

restart: ## Restart all services
	bash scripts/dev.sh restart

verify: ## Verify configuration
	bash scripts/verify_config.sh

logs: ## Tail backend logs
	bash scripts/dev.sh logs

logs-fe: ## Tail frontend logs
	bash scripts/dev.sh logs-fe

test: test-backend test-frontend ## Run all tests (backend + frontend unit)

test-backend: ## Run backend pytest suite
	cd $(BACKEND) && $(PY) -m pytest tests/ -q

test-frontend: ## Run frontend unit tests
	cd $(FRONTEND) && npm run test:unit

test-fast: ## Run fast subset of frontend unit tests
	cd $(FRONTEND) && npm run test:fast

test-e2e: ## Run Playwright e2e suite
	cd $(FRONTEND) && npm run test:e2e:all

lint: ## Run all linters (ruff, prettier, tsc, eslint)
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit run --all-files; \
	else \
		echo "pre-commit not found — running direct linters"; \
		cd $(BACKEND) && $(VENV)/ruff check . 2>/dev/null || echo "  (install ruff in backend venv: pip install ruff)"; \
		cd $(FRONTEND) && npm run lint; \
		cd $(FRONTEND) && npx tsc --noEmit; \
	fi

lint-fix: ## Auto-fix lint issues (eslint --fix; ruff --fix if available)
	cd $(FRONTEND) && npm run lint:fix
	@if [ -x "$(VENV)/ruff" ]; then cd $(BACKEND) && $(VENV)/ruff check --fix .; fi
	@if command -v pre-commit >/dev/null 2>&1; then pre-commit run --all-files || true; fi

db-init: ## Initialize database schema
	cd $(BACKEND) && ./manage db init

db-migrate: ## Run alembic migrations
	cd $(BACKEND) && ./manage db upgrade
