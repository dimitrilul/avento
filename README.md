# Avento

Avento ist eine private Full-Stack-Plattform für Radfahranalyse und
Streckenvisualisierung. Eine native Android-App und eine responsive Web-App
greifen auf dasselbe FastAPI-Backend zu. Importierte TCX-Dateien werden
serverseitig gespeichert, analysiert, mit historischen Wetterdaten angereichert
und optional durch eine KI-Zusammenfassung ergänzt.

## Komponenten

- `backend/`: FastAPI, SQLAlchemy, PostgreSQL, TCX-Analyse, Open-Meteo und OpenAI
- `web/`: React, TypeScript, Material UI, MapLibre und Recharts
- `android/`: Kotlin, Jetpack Compose und Material 3
- `infra/`: Caddy als TLS-fähiger Reverse Proxy

## Produktiver Start mit Docker

Voraussetzungen sind Docker mit Compose sowie eine Domain oder `localhost` für
den ersten Test.

```bash
cp .env.example .env
# POSTGRES_PASSWORD, SECRET_KEY, BOOTSTRAP_INVITE_CODE und PUBLIC_URL setzen
newgrp docker
docker compose up --build -d
```

Anschließend ist Avento unter `PUBLIC_URL` erreichbar. Der in
`BOOTSTRAP_INVITE_CODE` konfigurierte Code ermöglicht die Erstellung des ersten
Administratorkontos. Ohne `OPENAI_API_KEY` wird eine lokale, regelbasierte
Zusammenfassung erzeugt; die restliche App bleibt vollständig nutzbar.

## Entwicklung

Backend:

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
uvicorn app.main:app --reload
```

Web-App:

```bash
cd web
npm install
npm run dev
```

Android:

```bash
cd android
./gradlew testDebugUnitTest assembleDebug \
  -Pavento.apiBaseUrl=http://10.0.2.2:8000/api/v1/
```

Die erzeugte Debug-APK liegt nach dem Build unter
`android/app/build/outputs/apk/debug/app-debug.apk`. Weitere Android-Hinweise
stehen in [`android/README.md`](android/README.md).

Eine kleine TCX-Beispieldatei zum Ausprobieren liegt unter
[`examples/sample-ride.tcx`](examples/sample-ride.tcx).

## Qualität und Betrieb

```bash
make test
make backup
```

Uploads und PostgreSQL-Daten liegen in Docker-Volumes. `scripts/backup.sh`
sichert Datenbank und originale TCX-Dateien im lokalen Verzeichnis `backups/`.
API-Schlüssel, Passwörter und Token gehören ausschließlich in `.env` und niemals
ins Repository.
