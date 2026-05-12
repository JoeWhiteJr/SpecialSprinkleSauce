.PHONY: dev-backend dev-frontend test-backend test-frontend test lint-backend lint-frontend lint build docker-up docker-down typecheck ci hooks-install hooks-run

# Development
dev-backend:
	cd backend && TRADING_MODE=paper USE_MOCK_DATA=true uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# Testing
test-backend:
	cd backend && TRADING_MODE=paper USE_MOCK_DATA=true python -m pytest -v --tb=short

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

# Linting
lint-backend:
	cd backend && ruff check . --select=E,F,W --ignore=E501

lint-frontend:
	cd frontend && npm run lint

lint: lint-backend lint-frontend

# Build
build:
	cd frontend && npm run build

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Type checking
typecheck:
	cd frontend && npx tsc --noEmit

# Full CI simulation
ci: hooks-run lint typecheck test build
	@echo "All CI checks passed!"

# Pre-commit hooks — run once after a fresh clone.
#
# The repo-root pre-commit framework is the AUTHORITATIVE hook runner:
# it owns .git/hooks/pre-commit and invokes lint-staged via the
# `frontend-lint-staged` local hook in .pre-commit-config.yaml.
#
# Husky is installed in frontend/ as a supplementary hook for devs who
# only work in the frontend. We deliberately do NOT run `npx husky init`
# here because that would set git's core.hooksPath to frontend/.husky and
# silently bypass the root pre-commit framework (and its secret scan).
hooks-install:
	pre-commit install
	pre-commit install --hook-type commit-msg
	cd frontend && npm install
	# Create the husky hook file so it's available if a dev chooses to
	# opt-in by running `cd frontend && npx husky` themselves.
	mkdir -p frontend/.husky
	printf '%s\n' '#!/usr/bin/env sh' '# Supplementary frontend hook (NOT installed by default).' '# To activate: cd frontend && npx husky' 'cd "$$(dirname "$$0")/.."' 'npx --no-install lint-staged' > frontend/.husky/pre-commit
	chmod +x frontend/.husky/pre-commit
	@echo "Hooks installed. Run 'make hooks-run' to test against all files."

# Run all hooks against the whole repo (useful in CI and after big merges).
hooks-run:
	pre-commit run --all-files
