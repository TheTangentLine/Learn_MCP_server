.PHONY: clone-repos build run

clone-repos:
	@echo "Cloning repositories..."
	python3 src/cloner.py

build:
	docker compose build

run: clone-repos build
	docker compose up
