# GitHub-Veröffentlichung – ganz einfach

Das Repository ist lokal fertig und enthält **keine VIN, keine Rohdaten,
keine Secrets und keine privaten Pfade**.

## Einmalig veröffentlichen

1. **GitHub Desktop** öffnen (ist installiert).
2. Falls noch kein Konto: **Create your free account** und E-Mail bestätigen.
   Danach anmelden.
3. **File → Add Local Repository**.
4. Ordner auswählen:
   `%USERPROFILE%\Desktop\Volvo-CAN-Public`
5. GitHub Desktop erkennt das Repository. Oben auf
   **Publish repository** klicken.
6. Name: **`volvo-can-diagnostics`**
7. **Keep this code private NICHT anhaken** – das Repository soll öffentlich
   sein.
8. **Publish repository** klicken.

Fertig. Oben rechts erscheint der Link, z. B.
`https://github.com/DEINNAME/volvo-can-diagnostics`.

## Spätere Änderungen

1. GitHub Desktop öffnen.
2. Links unter **Changes** die Änderungen prüfen.
3. Kurze Beschreibung eintragen → **Commit to main**.
4. Oben **Push origin** klicken.

## Wichtig

- Keine `messungen/`, `SAVE_*`, CSV-/JSONL-Rohdaten, `secrets.h`, `.venv` oder
  `.pio` hinzufügen.
- Keine VIN, keine Screenshots mit Fahrzeugdaten und keine WLAN-Passwörter
  veröffentlichen.
- Die `.gitignore` schützt bereits vor den wichtigsten Daten.
- Öffentlich sind nur Code, Doku, Hardware-/CAN-Bus-Infos, Modell, Modelljahr
  und T8-Variante.
