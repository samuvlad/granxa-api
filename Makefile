.PHONY: up down build logs shell api-shell migrate test restart clean

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

api-shell:
	docker compose exec api bash

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest

restart:
	docker compose restart api

clean:
	docker compose down -v
