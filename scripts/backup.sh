#!/usr/bin/env sh
set -eu

backup_dir="${1:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"

docker compose exec -T database pg_dump \
  --username "${POSTGRES_USER:-avento}" \
  --dbname "${POSTGRES_DB:-avento}" \
  --format custom > "$backup_dir/avento-$timestamp.dump"

docker compose exec -T backend \
  tar -czf - -C /var/lib/avento uploads > "$backup_dir/avento-uploads-$timestamp.tar.gz"

echo "Backup erstellt: $backup_dir/avento-$timestamp.dump"
echo "Uploads einschließlich TCX-Dateien und Fotos gesichert: $backup_dir/avento-uploads-$timestamp.tar.gz"
