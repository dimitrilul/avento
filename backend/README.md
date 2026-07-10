# Avento Backend

FastAPI-API für Anmeldung, TCX-Import, serverseitige Auswertung, Wetter und Aktivitätszusammenfassungen.

## Lokal starten

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Für eine einfache lokale SQLite-Instanz kann `AVENTO_DATABASE_URL=sqlite:///./avento.db` und
`AVENTO_AUTO_CREATE_SCHEMA=true` gesetzt werden. In Produktion müssen mindestens eine PostgreSQL-URL,
ein zufälliger `AVENTO_SECRET_KEY` sowie ein `AVENTO_BOOTSTRAP_INVITE_CODE` konfiguriert werden.

## Authentifizierung

Der erste Benutzer wird einmalig über `POST /api/v1/auth/bootstrap` mit `bootstrap_code` angelegt und ist
Administrator. Weitere Benutzer erhalten über `POST /api/v1/auth/invitations` eine Einladung. Access-Tokens
werden als Bearer-Token gesendet; Refresh-Tokens werden bei jeder Erneuerung rotiert.

Administratoren können über `POST /api/v1/auth/password-resets` einen einmaligen Passwort-Reset-Token
ausstellen. Der Token wird nur in dieser Antwort angezeigt und in der Datenbank ausschließlich gehasht
gespeichert. Ein erfolgreicher Reset über `POST /api/v1/auth/password-reset` sowie ein authentifizierter
Passwortwechsel über `POST /api/v1/profile/password` widerrufen alle Refresh-Sitzungen des Benutzers.

Ohne OpenAI-Schlüssel erstellt der Server eine deterministische lokale Zusammenfassung. Mit
`AVENTO_OPENAI_API_KEY` verwendet er die Responses API und standardmäßig `gpt-5.4-mini`. Wetter wird anhand
der ersten Streckenkoordinate und Startzeit über Open-Meteo ergänzt; ein nicht erreichbarer Anbieter verhindert
den TCX-Import nicht.

Die interaktive API-Dokumentation ist unter `/docs` verfügbar.
