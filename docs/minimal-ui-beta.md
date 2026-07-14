# Minimal UI (Beta)

## Zielbild

Die Minimal UI ist eine optionale Präsentationsschicht für die Avento-Web-App. Sie soll sich wie ein ruhiges, persönliches Trainingsjournal anfühlen: wenige visuelle Container, klare Typografie, großzügiger Abstand und das bestehende Avento-Türkis als gezielter Akzent.

Phase 1 ersetzt die klassische Oberfläche nicht. Sie gestaltet ausschließlich Navigation, Dashboard und Meilensteine neu. Alle bestehenden URLs, Datenabfragen, Berechnungen und Aktionen bleiben erhalten.

## Aktivierung und Persistenz

Der Schalter befindet sich unter **Profil → Einstellungen → Experimente**. Aktivieren erfordert eine Bestätigung; Deaktivieren stellt Classic ohne zusätzlichen Dialog wieder her. Der aktuelle Pfad bleibt bei beiden Wechseln erhalten.

Der Modus wird als `users.ui_mode` mit den erlaubten Werten `classic` und `minimal` gespeichert. `classic` ist Datenbank-, Schema- und Frontendstandard. Lesen und Schreiben erfolgen über den bestehenden Endpunkt `GET/PATCH /api/v1/profile`; ein eigener Feature-Flag-Endpunkt ist nicht nötig.

Die bestehende lokale Farbpräferenz `avento-color-mode` bleibt unabhängig. Minimal UI verwendet in Phase 1 immer Dark. Nach dem Zurückschalten stellt Classic die zuvor gewählte Farbpräferenz wieder her.

## Technische Trennung

- `UiModeProvider` liest den Modus aus dem angemeldeten Profil, speichert Änderungen über die Profil-API und wählt das aktive MUI-Theme.
- `AppShell` wählt zentral zwischen Classic- und Minimal-Shell. Die UI-Komponenten enthalten keine verstreuten `minimalUiEnabled`-Abfragen.
- `App` wählt nur für `/` und `/meilensteine` eigene Minimal-Seiten. Nicht migrierte Routen laufen im Minimal-Shell innerhalb einer `ClassicContentBoundary` mit klassischem Dark Theme.
- `data-ui-mode="classic|minimal"` kapselt globale Minimal-CSS-Regeln. Classic erhält keine Minimal-Overrides.
- Android ignoriert das zusätzliche Profilfeld und bleibt unverändert.

## Design-Tokens

Die Tokens werden zentral in `createMinimalTheme()` erzeugt:

| Bereich | Phase-1-Definition |
| --- | --- |
| Hintergrund | `#090E0D` |
| Oberfläche | `#111817`, subtil `#0D1413`, hervorgehoben `#17201F` |
| Primärtext | `#F3F7F6` |
| Sekundärtext | `#96A5A2` |
| Avento-Akzent | `#65C8C1` |
| Abstände | 4, 8, 12, 16, 24, 32, 48 und 64 px |
| Rundungen | 8, 12 und 16 px je nach Hierarchie |
| Inhaltsbreite | maximal 1280 px |
| Typografie | Manrope Variable mit responsiven Hero-, Kennzahl- und Abschnittsstufen |
| Bewegung | 120, 180 und 240 ms; unter `prefers-reduced-motion` praktisch deaktiviert |
| Fokus | 2 px Avento-Türkis mit sichtbarem Abstand |
| Diagramme | Türkis als Hauptverlauf, ruhiges Blau, Lime, Amber und Coral ergänzend |

Die bestehenden MUI-Breakpoints bleiben erhalten. Zusätzlich wird eine Mindestbreite von 320 px ohne horizontalen Overflow getestet.

## Komponenten und Verhalten

### Minimal-Shell

Desktop verwendet eine 216 px breite Navigation. Tablet und Mobile verwenden Kopfleiste und Drawer. Ziele, URLs, Admin-Navigation, Importaktion und Profilzugang entsprechen Classic. Das Badge **„Minimal UI · Beta“** öffnet einen fokussierten Informationsdialog.

### Dashboard

Die Seite ordnet bestehende Daten neu: persönliche Begrüßung, Wochenfortschritt, großer Distanzverlauf, Trainingsimpuls, letzte Aktivität mit Trackkarte und ergänzende Kennzahlen. Fehlende Insights, Trackpunkte oder Aktivitäten erhalten ruhige Leerzustände.

### Meilensteine

Level und XP bleiben sichtbar, bestimmen aber nicht mehr die gesamte Seite. Jahresmomente und persönliche Rekorde stehen vor Zielen, Trainingsempfehlungen, Rhythmus, Entdeckungen und Abzeichen. Ziel- und Challenge-Mutationen verwenden unverändert die bestehenden API-Funktionen und Dialoge. Sicherheits- und Erholungshinweise bleiben deutlich sichtbar.

## Tests und visuelle Referenzen

```bash
cd backend && .venv/bin/python -m pytest
cd web && npm test
cd web && npm run build
cd web && npm run test:e2e
```

Vitest deckt Provider, Persistenzschnittstelle, Bestätigungsdialog, Abbruch, Theme-Auswahl, Classic-Isolation, Badge und Tastaturschließen ab. Backendtests decken Standardwert, Speicherung, erneutes Lesen und ungültige Werte ab.

Playwright startet eine isolierte SQLite-Instanz, legt über die echte API ein Konto an und importiert `examples/sample-ride.tcx`. Die Browserprüfung umfasst Aktivierung, Reload, neuen Browserkontext, Deaktivierung, Navigation, Dialog, 320-px-Overflow und Screenshot-Vergleich.

Versionierte Referenzen liegen unter `web/e2e/minimal-ui.spec.ts-snapshots/`:

- Classic-Dashboard: 1440×1000, 834×1112 und 390×844
- Minimal-Dashboard: 1440×1000, 834×1112 und 390×844
- Minimal-Meilensteine: 1440×1000 und 390×844
- Minimal-Beta-Dialog: 390×844

Neue Referenzen werden bewusst mit `npm run test:visual:update` erzeugt und anschließend visuell geprüft.

## Bekannte Einschränkungen und Folgephasen

- Minimal UI unterstützt zunächst nur Dark Theme.
- Aktivitäten, Aktivitätsdetails, Entwicklung, Rekorde, Statistiken, Vergleich, Avento Chat, Profilinhalte und MCP-Verwaltung verwenden noch die klassische Inhaltsdarstellung.
- Die Trackkarte benötigt den konfigurierten Kartenstil beziehungsweise den bestehenden externen Standardstil.
- Der vorhandene Dashboard-Wochenrichtwert von 100 km wurde nicht als neue Geschäftslogik verändert.
- Die native Android-App ist nicht Teil dieser Beta.

Weitere Seiten werden erst nach ausdrücklicher Freigabe migriert.

## Beta entfernen oder zum Standard machen

Zum Entfernen werden Minimal-Routen, Minimal-Shell, Theme und Provider-Auswahl entfernt. `ui_mode` kann zunächst kompatibel im Profil verbleiben und später in einer eigenen Migration entfallen.

Für eine Übernahme als Standard wird zuerst der Serverstandard auf `minimal` geändert und für Bestandskonten bewusst migriert. Nach einer Übergangsphase kann die Classic-Grenze pro Seite abgebaut werden. Classic wird erst entfernt, wenn alle noch klassischen Routen funktional und visuell migriert sowie bestehende gespeicherte Präferenzen behandelt sind.
