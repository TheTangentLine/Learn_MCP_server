.PHONY: clone-repos build run logs down

clone-repos:
	@echo "Cloning repositories..."
	python3 src/cloner.py

build:
	docker compose build

run: clone-repos build
	docker compose up -d

logs:
	docker compose logs -f mcp-server

down:
	docker compose down
