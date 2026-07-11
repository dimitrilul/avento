.PHONY: up deploy down logs test backup restore

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

restore:
	@test -n "$(BACKUP_DB)" || (echo "Verwendung: make restore BACKUP_DB=... BACKUP_UPLOADS=..." >&2; exit 2)
	./scripts/restore.sh "$(BACKUP_DB)" "$(BACKUP_UPLOADS)"
