# Datenschutz- und Sicherheitskonzept für Google Health

Stand: 12. Juli 2026

## Geltungsbereich

Dieses Konzept gilt ausschließlich für die cloudbasierte Google Health API v4. Health Connect und Google Fit sind nicht Teil der Implementierung. Avento verarbeitet Fitness-, Schlaf- und Recovery-Signale als private Wellness-Daten. Scores sind keine Diagnose, keine Krankheitswahrscheinlichkeit und keine medizinische Handlungsempfehlung.

Die verbindlichen Google-Grundlagen sind die [Google Health API Developer and User Data Policy](https://developers.google.com/health/policy), die [OAuth-Sicherheitspraktiken](https://developers.google.com/identity/protocols/oauth2/resources/best-practices), die [Restricted-Scope-Anforderungen](https://support.google.com/cloud/answer/13464325) und die [App-Verifizierung](https://developers.google.com/health/app-verification).

## Datenfluss und Zweckbindung

1. Ein authentifizierter Avento-Nutzer startet den OAuth-Flow.
2. Das Backend erzeugt State und S256-PKCE und tauscht den Callback-Code serverseitig aus.
3. Tokens werden nur verschlüsselt im Backend gehalten.
4. Der API-Client liest ausschließlich freigegebene Read-only-Datentypen.
5. Externe Antworten werden gegen eine Whitelist von Typen, Einheiten, Wertebereichen und Zeitfeldern validiert.
6. Hochauflösende Herzfrequenzdaten werden im Arbeitsspeicher zu Minuten-, Stunden-, Tages-, Schlaf- und Trainingsmerkmalen verdichtet; ungefilterte Provider-Payloads werden nicht dauerhaft gespeichert.
7. Normalisierte Daten und Scores sind strikt dem lokalen `user_id` zugeordnet.

Zulässige Zwecke sind persönliche Fitnessübersicht, Schlafauswertung, Recovery, Energie, Trainingsbelastung und langfristige Resilienz. Eine Weitergabe, Werbung, Kredit-/Versicherungsentscheidung oder medizinische Profilbildung ist nicht vorgesehen.

## OAuth- und Token-Schutz

- State ist zufällig, gehasht gespeichert, kurzlebig, einmalig und an Nutzer sowie Redirect-URI gebunden.
- PKCE verwendet S256; Klartext-Challenges sind unzulässig.
- Redirect-URIs stammen ausschließlich aus Serverkonfiguration und werden exakt verglichen.
- Google-Client-Secret, Access- und Refresh-Tokens erscheinen nie in URLs, Browser-State, Android-Speicher, Logs oder Fehlermeldungen.
- Tokenverschlüsselung verwendet einen separaten, versionierten Schlüssel. Schlüsselrotation muss alte Chiffrate während einer kontrollierten Migration noch entschlüsseln können.
- Refresh erfolgt kurz vor Ablauf; ein optional rotierter Refresh-Token wird atomar ersetzt.
- `invalid_grant` und Widerruf führen zu einem sicheren Status ohne automatischen Zustimmungsloop.
- Beim Trennen wird der Grant bestmöglich widerrufen und das lokale Chiffrat gelöscht.

Der offizielle Web-Server-Flow und Widerruf sind unter [Using OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server) beschrieben.

## Mandantentrennung und Autorisierung

Jeder Health-Endpunkt verlangt eine gültige Avento-Anmeldung. Datenbankabfragen filtern zusätzlich nach der `user_id` des aktuellen Nutzers. Externe IDs sind keine Autorisierungsmerkmale. Fremde Datensätze werden nicht bestätigt und ergeben einen neutralen 404- beziehungsweise leeren Nutzerkontext.

Für jede Ressource gelten zusammengesetzte Unique Constraints mit Verbindung/Nutzer. Tests müssen mindestens zwei Nutzer anlegen und Lesen, Synchronisieren, Trennen und Löschen über Mandantengrenzen hinweg abweisen.

## Datenminimierung und Aufbewahrung

- Nur drei erforderliche Read-only-Scopes.
- Keine Profil-, Standort-, Schreib-, EKG- oder medizinischen Scopes.
- Keine ungefilterten Google-Antworten in der Datenbank.
- Externe Namen und IDs werden, soweit für Herkunft/Idempotenz ausreichend, gehasht oder auf harmlose Geräteanzeigewerte reduziert.
- Page-Tokens sind opak, werden nie geloggt und nicht als dauerhafte fachliche Cursor betrachtet.
- Deduplizierung verwendet Provider-ID-Hash oder einen kanonischen Inhalts-/Zeit-Hash.
- Roh-Herzfrequenz wird nach erfolgreicher Aggregation verworfen.
- Audit enthält Status, Zähler und bereinigte Fehlerklassen, aber keine Gesundheitswerte oder Tokens.

Aufbewahrungsfristen müssen vor öffentlichem Betrieb festgelegt und technisch durchgesetzt werden. Backups enthalten normalisierte Gesundheitsdaten und unterliegen denselben Lösch- und Zugriffsvorgaben.

## Löschung

Der Nutzer kann Verbindung und importierte Google-Health-Daten löschen. Der Ablauf ist idempotent:

1. Verbindung gegen weitere Synchronisation sperren.
2. Google-Grant bestmöglich widerrufen.
3. Tokenchiffrate und OAuth-Sitzungen löschen.
4. Quellen, Geräte, Cursor, Lücken, Messungen, Schlaf, Aggregate und Scores transaktional löschen.
5. Nur einen nicht identifizierenden Abschlussstatus ohne Gesundheitsdaten behalten.

Ein fehlgeschlagener externer Widerruf darf die lokale Löschung nicht verhindern; er wird bereinigt protokolliert. Offizielle Referenz: [OAuth token revocation](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke).

## Synchronisationssicherheit

- HTTPS, feste Google-Basis-URL und feste Host-Allowlist im Echtbetrieb.
- Kurze Verbindungs-/Antwort-Timeouts und begrenzte Antwortgrößen.
- Vollständige Pagination mit unveränderten Filtern und opakem `nextPageToken`.
- Nutzerbezogenes Rate Limit für Start, Callback, manuellen Sync und Löschung.
- HTTP 429 und vorübergehende 5xx-Antworten: begrenzter exponentieller Backoff mit Jitter und `Retry-After`.
- Keine Retries für Authentifizierungs-, Autorisierungs- oder Validierungsfehler.
- Wasserstand erst nach vollständiger, erfolgreicher Seitenfolge verschieben.
- Rollendes Überlappungsfenster für verspätete oder geänderte Daten; Upsert bleibt idempotent.

Google nennt die aktuellen Nutzerquoten unter [Rate limits](https://developers.google.com/health/rate-limits).

## Validierung und sichere Fehler

Zeitpunkte werden als zeitzonenbewusste UTC-Werte normalisiert; Offset und Herkunftszeitzone bleiben nachvollziehbar. Unplausible Bereiche, unbekannte Einheiten, leere Intervalle, zu große Seiten und unbekannte Datentypen werden verworfen und nur als Zähler erfasst. Schlafphasen müssen innerhalb der Sitzung liegen. Überlappende Quellen werden nach einer festen Priorität kanonisiert und nicht blind addiert.

Fehlermeldungen an Clients verwenden stabile, deutschsprachige Codes. Provider-Response-Bodies, Request-Header, OAuth-Code, State, Page-Token und Chiffrate dürfen nicht enthalten sein.

## Deterministische Scores

Recovery, Energie, Trainingsbelastung und Resilienz werden ausschließlich deterministisch berechnet. Jede Ausgabe enthält Algorithmusversion, Datenabdeckung, persönliche 7-/14-/30-Tage-Baseline, Einflussfaktoren und Unsicherheit. Fehlen zentrale Signale oder Mindestdaten, wird kein Zahlenwert ausgegeben. KI darf ausschließlich eine bereits berechnete Datengrundlage erklären und niemals den Score erzeugen oder verändern.

Jede Darstellung enthält einen Hinweis, dass es sich um eine Wellness-/Fitness-Einschätzung und nicht um eine medizinische Aussage handelt.

## Logging, Monitoring und Incident Response

Zulässige Betriebsmetriken: Laufzeit, HTTP-Statusklasse, Retry-Zahl, Anzahl importierter/aktualisierter/abgewiesener Punkte, Datentyp und pseudonyme lokale Lauf-ID. Unzulässig: Tokens, externe Nutzer-ID, Provider-Payload, genaue Messwerte, Schlafzeiten und ungehashte Geräte-/Quellen-IDs.

Bei einem vermuteten Tokenabfluss:

1. Synchronisation deaktivieren.
2. betroffene Grants widerrufen und Client-Secret beziehungsweise Token-Schlüssel rotieren;
3. Logs und Backups auf Offenlegung prüfen;
4. betroffene Nutzer und zuständige Stellen nach dem anwendbaren Recht informieren;
5. Ursache beheben und kontrolliert wieder freigeben.

## Produktionsfreigabe-Checkliste

- [ ] Drei minimale Restricted Read-only-Scopes, keine weiteren Scopes
- [ ] Exakte HTTPS-Redirect-URI und keine offenen Redirects
- [ ] Separate, versionierte Tokenverschlüsselung und getestete Rotation
- [ ] Mandantentrennungs- und Löschtests bestanden
- [ ] Rate Limits, Retry-Grenzen und sichere Fehler aktiv
- [ ] Keine Secrets oder Gesundheitswerte in Logs und Frontend-State
- [ ] Backup-, Restore- und Löschkonzept getestet
- [ ] In-App-Offenlegung gut sichtbar
- [ ] Datenschutzrichtlinie, Nutzungsbedingungen und bestätigte Domains bereit
- [ ] OAuth-Verifizierung geplant, aber bewusst extern ausgelöst
- [ ] CASA nur auf Aufforderung von Google Trust & Safety begonnen
- [ ] Mockmodus und Debug-Logging in Produktion deaktiviert
- [ ] Wellness-/Nicht-Medizin-Hinweise in allen Scoreansichten

Vor jeder Freigabe sind die [Google-Health-Release-Notes](https://developers.google.com/health/release-notes), die [Datentyp-Matrix](https://developers.google.com/health/data-types) und die [App-Verifizierung](https://developers.google.com/health/app-verification) erneut zu prüfen.
