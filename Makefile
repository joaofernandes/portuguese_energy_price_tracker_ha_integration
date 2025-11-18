.PHONY: help dev-up dev-down dev-restart dev-logs dev-clean dev-shell validate

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev-up: ## Start development environment
	@echo "Starting Home Assistant development environment..."
	docker-compose up -d
	@echo "Home Assistant is starting up..."
	@echo "Access it at: http://localhost:8123"
	@echo "View logs: make dev-logs"

dev-down: ## Stop development environment
	@echo "Stopping Home Assistant development environment..."
	docker-compose down

dev-restart: ## Restart Home Assistant container
	@echo "Restarting Home Assistant..."
	docker-compose restart
	@echo "Home Assistant restarted. View logs: make dev-logs"

dev-logs: ## Follow logs from Home Assistant
	docker-compose logs -f

dev-logs-integration: ## Follow integration-specific logs
	docker-compose logs -f | grep --line-buffered portuguese_energy_price_tracker

dev-clean: ## Stop and remove all containers, volumes, and dev data
	@echo "Cleaning development environment..."
	docker-compose down -v
	rm -rf dev_config/.storage dev_config/*.db* dev_config/*.log custom_components/portuguese_energy_price_tracker/data/
	@echo "Development environment cleaned"

dev-shell: ## Open a shell in the Home Assistant container
	docker exec -it portuguese_energy_price_tracker_dev bash

dev-rebuild: ## Rebuild and restart containers
	@echo "Rebuilding containers..."
	docker-compose up -d --build

validate: ## Validate integration with hassfest
	@echo "Running hassfest validation..."
	docker run --rm \
		-v $(PWD)/custom_components:/custom_components \
		ghcr.io/home-assistant/home-assistant:stable \
		python -m script.hassfest --integration-path /custom_components/energy_price_tracker

test: ## Run basic integration tests
	@echo "Testing integration..."
	@echo "1. Checking Python syntax..."
	python3 -m py_compile custom_components/energy_price_tracker/*.py
	@echo "2. Checking manifest..."
	python3 -c "import json; json.load(open('custom_components/energy_price_tracker/manifest.json'))"
	@echo "All tests passed!"

watch: ## Watch logs and auto-restart on code changes
	@echo "Watching for changes and auto-restarting..."
	@echo "Press Ctrl+C to stop"
	@which fswatch > /dev/null || (echo "fswatch not installed. Install with: brew install fswatch" && exit 1)
	fswatch -o custom_components/energy_price_tracker/*.py | xargs -n1 -I{} sh -c 'echo "Change detected, restarting..." && make dev-restart'
