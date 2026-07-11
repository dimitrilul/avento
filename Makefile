.PHONY: up deploy down logs test backup

up:
	docker compose up --build -d

deploy:
	git pull
	docker compose pull
	docker compose up -d --remove-orphans

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
