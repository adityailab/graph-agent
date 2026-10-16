.PHONY: fmt check test db-up db-down

fmt:
	uv run ruff format .
	uv run ruff check --fix .

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest -q

test:
	uv run pytest -q

db-up:
	docker compose up -d --wait

db-down:
	docker compose down
