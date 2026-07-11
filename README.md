# Avento

Avento ist eine private Full-Stack-Plattform für Radfahranalyse und
Streckenvisualisierung. Eine native Android-App und eine responsive Web-App
greifen auf dasselbe FastAPI-Backend zu. Importierte TCX-Dateien werden
serverseitig gespeichert, analysiert, entlang der Strecke mit historischen Wetterdaten angereichert
und optional durch einen persönlichen KI-Coach ausgewertet.

## Komponenten

- `backend/`: FastAPI, SQLAlchemy, PostgreSQL, TCX-Analyse, Open-Meteo, OpenAI und Read-only-MCP
- `web/`: React, TypeScript, Material UI, MapLibre und Recharts
- `android/`: Kotlin, Jetpack Compose und Material 3
- `infra/`: Caddy als TLS-fähiger Reverse Proxy

## Produktiver Start mit Docker

Voraussetzungen sind Docker mit Compose sowie eine Domain oder `localhost` für
den ersten Test.

```bash
cp .env.example .env
# POSTGRES_PASSWORD, SECRET_KEY, BOOTSTRAP_INVITE_CODE und PUBLIC_URL setzen.
# POSTGRES_PASSWORD bitte als langen zufälligen alphanumerischen Wert wählen.
newgrp docker
docker compose up --build -d
```

Anschließend ist Avento unter `PUBLIC_URL` erreichbar. Der in
`BOOTSTRAP_INVITE_CODE` konfigurierte Code ermöglicht die Erstellung des ersten
Administratorkontos. Ohne `OPENAI_API_KEY` wird eine lokale, regelbasierte
Zusammenfassung erzeugt; die restliche App bleibt vollständig nutzbar.

## Analyse, Fotos und Rekorde

Avento berechnet persönliche 10-, 20-, 30-, 40- und 50-km-Rekorde direkt aus
den Trackpunkten. Hinzu kommen Langzeittrends, Monats- und Jahresvergleiche,
vorsichtig formulierte Muster zu Wetter, Herzfrequenz, Tempo und
Aktivitätsabständen sowie Saison- und Jahresrückblicke. Trinkmengen können pro
Aktivität dokumentiert werden. Aktivitätsfotos werden validiert, als WebP
gespeichert und optional über Aufnahmezeit und Koordinaten der Strecke
zugeordnet.

Jede Coach-Antwort und KI-Zusammenfassung liefert eine strukturierte
Datengrundlage mit Zeitraum, Aktivitäten, Kennzahlen, Methoden und bekannten
Einschränkungen.

## Read-only-MCP

Der Read-only-MCP unterstützt für entfernte HTTP-Clients jetzt OAuth 2.1 mit
Authorization Code, PKCE und automatisch rotierenden Refresh-Tokens. MCP-
Clients entdecken die Endpunkte über die OAuth-Metadaten und registrieren sich
bei Bedarf dynamisch; ein manuell kopiertes Client-Secret ist nicht mehr nötig.
Beim ersten Verbinden öffnet sich der Avento-Login mit einer Scope-Freigabe.

Der Streamable-HTTP-Endpunkt lautet `/api/v1/mcp/rpc`. Die Protected-Resource-
Metadaten liegen unter `/.well-known/oauth-protected-resource`; die OAuth-
Server-Metadaten liegen unter `/.well-known/oauth-authorization-server`.
`PUBLIC_URL` muss deshalb auf die von MCP-Clients erreichbare HTTPS-Adresse
zeigen. Für abweichende Setups kann `MCP_RESOURCE_URI` gesetzt werden.

Der bisherige Secret-Flow bleibt als Übergang für bereits eingerichtete Clients
erhalten. Administratoren verwalten diese Legacy-Clients weiterhin unter
`/administration/mcp`; ihre Secrets und Tokens werden ausschließlich gehasht
gespeichert und jede MCP-Anfrage landet ohne Roh-Tokens oder Secrets im
Audit-Log.

Der Streamable-HTTP-Endpunkt lautet `/api/v1/mcp/rpc`. Codex kann ihn
beispielsweise mit einem Token aus einer Umgebungsvariable verwenden:

```toml
[mcp_servers.avento]
url = "http://localhost/api/v1/mcp/rpc"
# OAuth-fähige MCP-Clients starten die Anmeldung automatisch.
# Für einen Legacy-Client bleibt bearer_token_env_var möglich.
```

Für einen ausschließlich lokal erreichbaren MCP-Prozess kann im
Backend-Verzeichnis zusätzlich `python mcp_server.py` gestartet werden. Er
bindet standardmäßig an `127.0.0.1:8765`. Andere Streamable-HTTP-fähige
MCP-Clients verwenden denselben Endpunkt und Bearer-Token.

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
./gradlew testDebugUnitTest assembleDebug
```

Beim ersten Start fragt die App nach der Adresse des Avento-Servers.

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
sichert Datenbank, originale TCX-Dateien und Aktivitätsfotos im lokalen Verzeichnis `backups/`.
API-Schlüssel, Passwörter und Token gehören ausschließlich in `.env` und niemals
ins Repository.

Ein vollständiges Restore wird mit beiden Backup-Dateien gestartet. Dabei werden
die aktuelle Datenbank und das Upload-Volume überschrieben:

```bash
make restore BACKUP_DB=backups/avento-<zeitstempel>.dump \
  BACKUP_UPLOADS=backups/avento-uploads-<zeitstempel>.tar.gz
```

Das Restore-Skript verlangt vor dem Überschreiben die Eingabe `RESTORE`.
