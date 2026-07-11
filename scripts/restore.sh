#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Verwendung: $0 <postgres-dump> [uploads-archiv.tar.gz]" >&2
  exit 2
fi
database_backup="$1"
uploads_backup="${2:-}"
[ -f "$database_backup" ] || { echo "Datenbank-Backup nicht gefunden: $database_backup" >&2; exit 1; }
[ -z "$uploads_backup" ] || [ -f "$uploads_backup" ] || { echo "Upload-Backup nicht gefunden: $uploads_backup" >&2; exit 1; }

echo "ACHTUNG: Die aktuelle Datenbank wird vollständig überschrieben."
[ -z "$uploads_backup" ] || echo "Das aktuelle Upload-Volume wird ebenfalls vollständig überschrieben."
printf "Zum Fortfahren RESTORE eingeben: "
read confirmation
[ "$confirmation" = "RESTORE" ] || { echo "Restore abgebrochen."; exit 1; }

docker compose stop gateway web backend >/dev/null
echo "Datenbank wird wiederhergestellt ..."
docker compose exec -T database pg_restore --clean --if-exists --no-owner --exit-on-error \
  --username "${POSTGRES_USER:-avento}" --dbname "${POSTGRES_DB:-avento}" < "$database_backup"

if [ -n "$uploads_backup" ]; then
  echo "Uploads werden wiederhergestellt ..."
  docker compose run --rm -T --no-deps backend sh -c \
    'rm -rf /var/lib/avento/uploads/* /var/lib/avento/uploads/.[!.]* /var/lib/avento/uploads/..?* && tar -xzf - -C /var/lib/avento/uploads' < "$uploads_backup"
fi

docker compose up -d
echo "Restore erfolgreich abgeschlossen."
