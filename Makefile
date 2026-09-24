# Business Management Portal - developer convenience targets
# These targets help with local development. Docker Compose is the preferred
# way to run the full environment (see README).

SHELL := powershell

.PHONY: help up down logs backend frontend migrate test

help: ## Show available commands
	@echo "Available targets:"
	@echo "  make up       - docker compose up --build"
	@echo "  make down     - docker compose down"
	@echo "  make logs     - follow all service logs"
	@echo "  make backend  - follow backend logs"
	@echo "  make frontend - follow frontend logs"
	@echo "  make migrate  - apply alembic migrations"
	@echo "  make test     - run backend tests in the container"

up: ## Build and start all services
	docker compose up --build

down: ## Stop all services
	docker compose down

logs: ## Tail logs for all services
	docker compose logs -f

backend: ## Tail backend logs
	docker compose logs -f backend

frontend: ## Tail frontend logs
	docker compose logs -f frontend

migrate: ## Apply database migrations
	docker compose exec backend alembic upgrade head

test: ## Run backend tests
	docker compose exec backend pytest