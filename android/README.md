# Avento Android

Native Android-App mit Kotlin, Jetpack Compose und Material 3. Die App verwendet
dieselbe REST-API wie die Web-App und speichert keine Aktivitäten dauerhaft auf
dem Gerät. Nur die Sitzungstoken werden in DataStore abgelegt und vorher mit einem
nicht exportierbaren AES-Schlüssel aus dem Android Keystore verschlüsselt.

## Lokaler Start

Voraussetzungen: JDK 17 oder neuer, Android SDK 36 und Build Tools 36.0.0.

```bash
./gradlew testDebugUnitTest assembleDebug \
  -Pavento.apiBaseUrl=http://10.0.2.2:8000/api/v1/
```

`10.0.2.2` verweist im Android-Emulator auf den Entwicklungsrechner. Für Release-
Builds muss eine HTTPS-URL angegeben werden. Klartext-HTTP ist nur im Debug-Build
freigeschaltet.

## Import

TCX-Dateien können über „TCX importieren“ oder über das Android-Teilen-Menü an
Avento übergeben werden. Die Datei wird direkt an das Backend hochgeladen; die
serverseitige Aktivität ist danach auch in der Web-App sichtbar.

## Sicherheit

Access- und Refresh-Token werden AES-GCM-verschlüsselt in Preferences DataStore
gespeichert. Der Schlüssel wird im Android Keystore erzeugt und ist nicht
exportierbar. Für eine Veröffentlichung sollten zusätzlich Geräteintegritäts-
prüfungen, Certificate Pinning mit geplanter Schlüsselrotation und eine explizite
Sitzungsverwaltung im Benutzerprofil ergänzt werden.

## API-Vertrag

Die konfigurierte Basis-URL muss auf `/api/v1/` enden. Verwendet werden die
Auth-Endpunkte für Login, Refresh, Einladung und Bootstrap (einschließlich
`bootstrap_code`) sowie den Token-basierten Passwort-Reset. Ein angemeldeter
Passwortwechsel ist außerdem über `profile/password` im Repository verfügbar.
Hinzu kommen die Aktivitäten-Endpunkte für Liste, Multipart-Upload, Detail,
Track, Bearbeiten und Löschen sowie `/weather`, `/summary` und
`/statistics/overview`. Fehler werden im FastAPI-Format `{"detail":"…"}` erwartet.

## Verifikation in dieser Arbeitsumgebung

Der vollständige Build wurde mit Android SDK 36 und Build Tools 36.0.0 geprüft:
`./gradlew testDebugUnitTest assembleDebug` läuft erfolgreich, alle fünf
Unit-Tests bestehen und die Debug-APK wird erzeugt.
