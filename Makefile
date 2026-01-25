up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

reset-db:
	docker compose down -v
	docker compose up -d --build
