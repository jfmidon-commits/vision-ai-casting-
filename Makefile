# Vision AI Casting - Makefile
.PHONY: help install dev build test lint clean deploy

help: ## Show this help
	@echo "Vision AI Casting - Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development
install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev: ## Start development environment with docker-compose
	docker-compose up -d
	@echo "Services starting..."
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000/docs"
	@echo "Database: localhost:5432"
	@echo "Redis:    localhost:6379"

dev-backend: ## Start only backend services (db + redis + backend)
	docker-compose up -d db redis
	@echo "Waiting for database..."
	@sleep 5
	cd backend && source venv/bin/activate 2>/dev/null || true && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Start only frontend
	cd frontend && npm run dev

# Database
migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create msg="description")
	cd backend && alembic revision --autogenerate -m "$(msg)"

db-reset: ## Reset database (WARNING: destroys all data)
	docker-compose stop db
	docker-compose rm -f db
	docker volume rm vision-ai-casting_postgres_data 2>/dev/null || true
	docker-compose up -d db
	@sleep 5
	cd backend && alembic upgrade head

# Testing
test: ## Run all tests
	@echo "Running backend tests..."
	cd backend && pytest -v --cov=app --cov-report=html --cov-report=term
	@echo "Running frontend tests..."
	cd frontend && npm test -- --watchAll=false --coverage

test-backend: ## Run backend tests only
	cd backend && pytest -v --cov=app --cov-report=term

test-frontend: ## Run frontend tests only
	cd frontend && npm test -- --watchAll=false

# Linting & Formatting
lint: ## Run all linters
	@echo "Linting backend..."
	cd backend && black --check app/ && isort --check-only app/ && flake8 app/ --max-line-length=120
	@echo "Linting frontend..."
	cd frontend && npm run lint

format: ## Format all code
	@echo "Formatting backend..."
	cd backend && black app/ && isort app/
	@echo "Formatting frontend..."
	cd frontend && npm run format

# Building
build: ## Build production images
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

build-frontend: ## Build frontend for production
	cd frontend && npm run build

# Deployment
deploy-staging: ## Deploy to staging
	@echo "Deploying to staging..."
	# aws ecs update-service --cluster vision-ai-staging --service backend --force-new-deployment

deploy-prod: ## Deploy to production (requires confirmation)
	@echo "WARNING: Deploying to production!"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	@echo "Deploying to production..."
	# aws ecs update-service --cluster vision-ai-prod --service backend --force-new-deployment

# Infrastructure
infra-init: ## Initialize Terraform
	cd infra && terraform init

infra-plan: ## Plan Terraform changes
	cd infra && terraform plan

infra-apply: ## Apply Terraform changes
	cd infra && terraform apply

# Utilities
clean: ## Clean up containers, volumes, and temp files
	docker-compose down -v --remove-orphans
	docker system prune -f
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "coverage" -exec rm -rf {} + 2>/dev/null || true

logs: ## Show logs from all services
	docker-compose logs -f

logs-backend: ## Show backend logs only
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs only
	docker-compose logs -f frontend

shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec db psql -U postgres -d vision_ai_casting

# Secrets management
secrets-encrypt: ## Encrypt secrets for production
	@echo "Encrypting .env files..."
	@# Implementation would use sops or similar tool

secrets-decrypt: ## Decrypt secrets for development
	@echo "Decrypting .env files..."
	@# Implementation would use sops or similar tool
