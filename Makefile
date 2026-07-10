.PHONY: up down logs test backup

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd backend && .venv/bin/python -m pytest
	cd web && npm test
	cd android && ./gradlew testDebugUnitTest

backup:
	./scripts/backup.sh
