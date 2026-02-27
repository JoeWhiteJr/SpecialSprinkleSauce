.PHONY: dev-backend dev-frontend test-backend test-frontend test lint-backend lint-frontend lint build docker-up docker-down typecheck ci

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
ci: lint typecheck test build
	@echo "All CI checks passed!"
