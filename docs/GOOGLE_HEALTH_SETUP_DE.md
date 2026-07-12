# Google Health API v4 in Avento einrichten

Stand: 12. Juli 2026

Dieser Leitfaden beschreibt ausschließlich die cloudbasierte **Google Health API v4**. Avento integriert weder Health Connect noch die alte Google-Fit-REST-API. Die Health API wurde im März 2026 als cloudbasierte Nachfolgerin der Fitbit Web API veröffentlicht. Maßgeblich sind die [Google-Health-Übersicht](https://developers.google.com/health), die [Release Notes](https://developers.google.com/health/release-notes) und der [Einrichtungsleitfaden](https://developers.google.com/health/setup).

## 1. Voraussetzungen

- Eine lokale oder selbst gehostete Avento-Installation mit erreichbarem Backend.
- Ein Google-Konto, das ein Google-Cloud-Projekt verwalten darf.
- Für echte Daten ein Google-Konto mit unterstützten Gesundheitsdaten, beispielsweise von Fitbit oder Pixel Watch.
- Eine feste Callback-URL. Lokal ist HTTP auf `localhost` zulässig; öffentlich muss HTTPS verwendet werden.
- Ein starker, eigener Schlüssel für die Verschlüsselung von Google-Tokens.

Avento beantragt nur Lesezugriff. Es werden keine kostenpflichtigen Dienste automatisch aktiviert, keine App veröffentlicht und keine Verifizierung eingereicht.

## 2. Google-Cloud-Projekt anlegen

1. Öffne die [Google-Health-Einrichtung](https://developers.google.com/health/setup).
2. Erstelle ein dediziertes Google-Cloud-Projekt für Avento. Ein eigenes Projekt begrenzt die Auswirkungen eines späteren OAuth-Widerrufs auf diese Integration.
3. Notiere die Projekt-ID, aber speichere keine heruntergeladene Credentials-Datei im Repository.

## 3. Google Health API aktivieren

Aktiviere im Projekt ausschließlich die **Google Health API**. Verwende weder Google Fit noch Health Connect. Der offizielle Einrichtungsassistent und die manuelle Aktivierung sind unter [Set up Google Cloud and OAuth](https://developers.google.com/health/setup) beschrieben.

## 4. OAuth-Zustimmungsseite konfigurieren

1. Wähle als Zielgruppe für private Tests `External` und als Veröffentlichungsstatus `Testing`.
2. Hinterlege App-Name, Support-E-Mail und Entwicklerkontakt.
3. Lege einen OAuth-Client vom Typ **Web application / Web Server** an. Nur das Avento-Backend ist Google-OAuth-Client.
4. Hinterlege später für den öffentlichen Betrieb bestätigte Domains, Datenschutzrichtlinie und Nutzungsbedingungen.

Google-Tokens, Client-Secret und Autorisierungscode gehören nie in Web- oder Android-State. Der Browser erhält von Avento lediglich die Google-Autorisierungs-URL. Details: [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server).

## 5. Erforderliche Restricted Scopes

Avento benötigt genau diese drei Read-only-Scopes:

```text
https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly
https://www.googleapis.com/auth/googlehealth.sleep.readonly
```

Sie decken Bewegung, Training, Kalorien, Herzfrequenzzonen, Herzfrequenz, HRV, Ruhepuls, Atemfrequenz, SpO₂, Schlaf und Schlafphasen ab. Avento fordert keine Schreib-, Profil-, Standort-, EKG- oder medizinischen Scopes an. Die aktuelle Zuordnung steht in der [Scope-Liste](https://developers.google.com/health/scopes) und der [Datentyp-Matrix](https://developers.google.com/health/data-types).

Die Scopes sind **restricted**. Trage sie in Google Cloud unter „Data Access“ ein. Für einen späteren öffentlichen Betrieb gelten die [Restricted-Scope-Anforderungen](https://support.google.com/cloud/answer/13464325).

## 6. Testnutzer hinzufügen

Unter „Audience“ muss der Status `Testing` sichtbar sein. Füge jede Google-E-Mail-Adresse, die sich verbinden soll, explizit unter „Test users“ hinzu. Unverifizierte Projekte sind auf 100 Nutzer begrenzt. Im Testing-Modus ausgegebene Refresh-Tokens laufen üblicherweise nach sieben Tagen ab; eine erneute Zustimmung ist dann erwartbar. Siehe [Google-Health-OAuth-Einrichtung](https://developers.google.com/health/setup).

## 7. Lokale Redirect-URIs

Der Callback muss exakt mit `AVENTO_GOOGLE_HEALTH_REDIRECT_URI` übereinstimmen. Beispiele:

```text
http://localhost:8000/api/v1/health/oauth/callback
http://localhost/api/v1/health/oauth/callback
https://avento.example.de/api/v1/health/oauth/callback
```

Registriere nur tatsächlich verwendete URIs. Keine Wildcards, offenen Weiterleitungen oder frei vom Client übergebenen Callback-Ziele. Bei Produktion ist HTTPS Pflicht. Google beschreibt den exakten URI-Abgleich im [Web-Server-OAuth-Leitfaden](https://developers.google.com/identity/protocols/oauth2/web-server).

## 8. Umgebungsvariablen

Die jeweils gültige Liste steht in `backend/.env.example` und der Root-`.env.example`. Für den Echtbetrieb werden mindestens benötigt:

```dotenv
AVENTO_GOOGLE_HEALTH_ENABLED=true
AVENTO_GOOGLE_HEALTH_MOCK_MODE=false
AVENTO_GOOGLE_HEALTH_CLIENT_ID=...
AVENTO_GOOGLE_HEALTH_CLIENT_SECRET=...
AVENTO_GOOGLE_HEALTH_REDIRECT_URI=http://localhost:8000/api/v1/health/oauth/callback
AVENTO_GOOGLE_HEALTH_TOKEN_ENCRYPTION_KEY=...
```

Der Verschlüsselungsschlüssel ist ein separater Fernet-Schlüssel und darf nicht mit `AVENTO_SECRET_KEY` oder dem Google-Client-Secret gleichgesetzt werden. Er darf niemals committed, geloggt oder an einen Client gesendet werden. Optionale Timeout-, Lookback- und Basis-URL-Werte sollten nur für Tests beziehungsweise einen kontrollierten Mock geändert werden.

Ohne Google-Zugangsdaten bleibt `AVENTO_GOOGLE_HEALTH_MOCK_MODE=true`. Der Mock führt keine externe Anmeldung aus und enthält keine echten Tokens.

## 9. Lokale Anwendung starten

```bash
cd backend
python -m pip install -e '.[test]'
uvicorn app.main:app --reload
```

In einem zweiten Terminal:

```bash
cd web
npm install
npm run dev
```

Für Docker werden die Variablen über die Root-`.env` an das Backend weitergereicht. Nach Konfigurationsänderungen muss der Backend-Prozess neu gestartet werden.

## 10. Erstmalige Google-Anmeldung

1. Melde dich zuerst bei Avento an.
2. Öffne „Gesundheit“ oder die Google-Health-Verbindung im Profil.
3. Lies die In-App-Offenlegung: Avento verwendet die gelesenen Fitness-, Schlaf- und Recovery-Signale ausschließlich für persönliche Wellness-Auswertungen.
4. Wähle „Mit Google Health verbinden“.
5. Avento erzeugt serverseitig einen kurzlebigen, einmaligen OAuth-State und S256-PKCE. Google-Tokens bleiben vollständig im Backend.

Der State ist an den angemeldeten Avento-Nutzer gebunden. Ein abgelaufener oder wiederverwendeter Callback wird abgewiesen.

## 11. Berechtigungen erteilen

Google zeigt die drei beantragten Read-only-Berechtigungen an. Erteile nur die benötigten Zugriffe. Avento setzt `access_type=offline`, damit eine spätere Synchronisation möglich ist. `prompt=consent` wird nur bei der ersten Verbindung, geänderten Scopes oder einer ausdrücklich notwendigen Neuausstellung des Refresh-Tokens verwendet. Siehe [Google-Health-Setup](https://developers.google.com/health/setup).

## 12. Synchronisation prüfen

Nach erfolgreichem Callback ruft Avento die Google-Health-Identität ab und startet eine initiale Synchronisation. Prüfe in „Datenquellen und Synchronisation“:

- Status `Verbunden`
- letzte erfolgreiche Synchronisation
- gelesene Scopes
- erkannte Geräte und Quellen
- Datenabdeckung und sichtbare Lücken
- importierte und deduplizierte Datensätze

Eine manuelle Synchronisation ist idempotent. Seiten werden über `nextPageToken` vollständig gelesen; der Wasserstand wird erst nach erfolgreicher letzter Seite fortgeschrieben. Details: [List-Endpunkt](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list), [Reconcile-Endpunkt](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile) und [Quoten](https://developers.google.com/health/rate-limits).

## 13. Token-Ablauf und erneute Anmeldung

Avento erneuert abgelaufene Access-Tokens serverseitig. Falls Google einen neuen Refresh-Token zurückgibt, wird er atomar verschlüsselt ersetzt; andernfalls bleibt der vorhandene erhalten. Bei `invalid_grant`, Widerruf oder endgültigem Ablauf wechselt die Verbindung auf „Erneute Anmeldung erforderlich“.

Im Testing-Modus ist ein Ablauf nach sieben Tagen normal. Fordere nicht unnötig wiederholt Zustimmung an; Google begrenzt die Zahl aktiver Refresh-Tokens. Siehe [OAuth-Tokenverhalten](https://developers.google.com/identity/protocols/oauth2) und [OAuth-Sicherheitspraktiken](https://developers.google.com/identity/protocols/oauth2/resources/best-practices).

## 14. Datenlöschung und Datentrennung

„Google Health trennen und Daten löschen“ versucht zuerst den OAuth-Grant bei Google zu widerrufen und entfernt danach lokal Token, normalisierte Messungen, Schlafdaten, Quellen, Geräte, Aggregate, Scores, Cursor und Sync-Lücken des angemeldeten Nutzers. Ein bereinigter Abschluss-Auditeintrag darf keine Gesundheitswerte, IDs oder Token enthalten.

Hochauflösende Herzfrequenzpunkte werden nur während der Synchronisation verarbeitet. Dauerhaft gespeichert werden Minuten-, Stunden-, Tages-, Schlaf- und Trainingsaggregate. Provider-Antworten werden nicht ungefiltert gespeichert. Der offizielle Widerruf ist unter [Token revocation](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke) beschrieben.

## 15. App-Verifizierung für öffentlichen Betrieb

Vor mehr als 100 Nutzern beziehungsweise einem öffentlichen Rollout ist die Google-Prüfung erforderlich. Bereite vor:

- bestätigte Domains, öffentliche Startseite, Datenschutzrichtlinie und Nutzungsbedingungen
- konkrete Begründung je Restricted Scope
- Video des vollständigen Zustimmungs- und Nutzungsablaufs
- sichtbare In-App-Offenlegung im normalen Verbindungsablauf
- funktionierende Datenlöschung und minimaler Datenzugriff

Sende die Verifizierung nicht aus dieser Entwicklungsarbeit ab. Folge erst im geplanten Rollout der [Google-Health-App-Verifizierung](https://developers.google.com/health/app-verification) und den [Verification Requirements](https://support.google.com/cloud/answer/13464321).

## 16. CASA- und Sicherheitsanforderungen

Restricted Health Scopes erfordern zusätzlich eine regelmäßige Sicherheitsbewertung nach CASA. Google Trust & Safety teilt mit, wann sie zu beginnen ist. Die aktuelle Google-Dokumentation nennt ungefähr zwei bis drei Wochen für Tier 2 und vier bis sechs Wochen für Tier 3 sowie derzeit 500 bis 4.500 US-Dollar externe Kosten; Werte und Einstufung können sich ändern. Maßgeblich bleibt [App verification – Security assessment](https://developers.google.com/health/app-verification).

CASA prüft unter anderem Zugriffskontrolle, Verschlüsselung, sichere Entwicklung, Logging, Incident Response und nachweisbare Datenlöschung. Vorher sollten Backups, Schlüsselrotation und Restore-Prozesse ausdrücklich auf Gesundheitsdaten geprüft werden.

## 17. Fehlerdiagnose

| Symptom | Wahrscheinliche Ursache | Maßnahme |
|---|---|---|
| `redirect_uri_mismatch` | Callback stimmt nicht exakt überein | Google-Cloud-URI und Env-Wert Zeichen für Zeichen vergleichen |
| `access_denied` | Nutzer oder Google verweigert Zugriff | Testnutzer und beantragte Scopes prüfen |
| „App nicht verifiziert“ | Restricted Scopes im Testprojekt | Tester explizit hinzufügen; öffentlichen Rollout nicht vortäuschen |
| Verbindung nach sieben Tagen getrennt | Testing-Refresh-Token abgelaufen | Erneut verbinden; für echten Betrieb Verifizierung planen |
| `invalid_grant` | Token abgelaufen, widerrufen oder Client geändert | Verbindung als getrennt behandeln und interaktiv neu autorisieren |
| HTTP 429 | Nutzerquote erreicht | Automatischen Retry mit `Retry-After`, exponentiellem Backoff und Jitter abwarten |
| Teilweise Daten | Quelle misst den Typ nicht oder verspätete Synchronisation | Abdeckung/Lücken prüfen, später mit Überlappungsfenster erneut synchronisieren |
| Kein Score | Kerndaten oder persönliche Baseline fehlen | Fehlende Faktoren und Mindestdatenanzeige beachten |

Google-Fehlertexte dürfen in Avento weder Tokens noch vollständige Provider-Antworten in Logs oder UI spiegeln. Weitere Hinweise: [Google-Health-Troubleshooting](https://developers.google.com/health/troubleshooting).

## 18. Wechsel von Test- zu Produktionsbetrieb

1. Sicherheits- und Datenschutzprüfung abschließen.
2. Öffentliche Domains, HTTPS, Richtlinien und In-App-Offenlegung fertigstellen.
3. OAuth-Verifizierung vorbereiten und erst bewusst absenden.
4. CASA erst auf Aufforderung von Google Trust & Safety starten.
5. Produktions-Redirect-URI separat registrieren.
6. Produktions-Secrets über einen Secret Manager oder die geschützte Laufzeitumgebung bereitstellen.
7. Mockmodus deaktivieren, Debug-Logging ausschalten und Quoten überwachen.
8. Schlüsselrotation, Backup-Löschung, Restore und Incident Response testen.
9. Zunächst mit einem internen Testnutzer verbinden und Sync, Löschung sowie erneute Anmeldung prüfen.
10. Erst danach schrittweise weitere Nutzer zulassen.

Die Google Health API ist seit März 2026 verfügbar, entwickelt sich aber weiter. Prüfe vor jedem Produktionsrollout die [Release Notes](https://developers.google.com/health/release-notes), die [Datentyp-Matrix](https://developers.google.com/health/data-types), die [Quoten](https://developers.google.com/health/rate-limits) und die [Verifizierungsseite](https://developers.google.com/health/app-verification).
