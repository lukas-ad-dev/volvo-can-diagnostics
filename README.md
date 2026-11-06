# Volvo CAN Diagnostics – CEM & OBD Low Bus

Passive CAN-Diagnose für einen **Volvo V90 T8 (SPA, Modelljahr 2021)** mit dem
Waveshare **ESP32-S3-RS485-CAN**. Das Repository enthält zwei getrennte
Projekte:

| Ordner | Bus | Inhalt |
|---|---|---|
| `OBD-CEM-Bus/` | interner CEM-CAN | Firmware, Web-GUI, Assistent, Doku |
| `OBD-Low-Bus/` | OBD-Diagnosebus (Pin 6/14) | ältere passive Analyse, Signalergebnisse, Tools |

## Öffentliche Daten – bewusst begrenzt

Veröffentlicht werden:

- Quellcode, Firmware, Web-Oberflächen, Tools und Tests
- CAN-Bus-Zuordnung, Hardwareinformationen und allgemeine Analyse-Doku
- Modell, Modelljahr und Motorvariante (V90 T8, MJ 2021)
- bereits geprüfte, allgemeine CAN-Erkenntnisse

**Nicht veröffentlicht:**

- VIN / Fahrgestellnummer
- Roh-Messdaten, CSV-/JSONL-Logs und Frame-Dumps
- WLAN-Passwörter, Secrets, Tokens
- private Windows-Pfade, Server-Zugänge oder Screenshots mit Fahrzeugdaten

Die `.gitignore` schließt Messdaten, Backups, Build-Artefakte und Secrets aus.

## Projektverlauf und Ergebnisse

- [`PROJEKTVERLAUF.md`](PROJEKTVERLAUF.md) – Fahrzeug, Ziel, Zeitlinie,
  Sicherheitsvorfall, offene Fragen
- [`ERGEBNISSE.md`](ERGEBNISSE.md) – CAN-IDs, Frame-Zahlen, Signal-Kandidaten,
  Hardware- und Sicherheitsstatus

## Sicherheit

- Ausschließlich **LISTEN_ONLY**, kein CAN-Senden.
- Keine Diagnoseanfragen, keine Gateway-Manipulation, keine Codierung.
- 500 kbit/s sind für den CEM-Test konfiguriert; kein Bitratenscan.
- Der echte CAN-TXD GPIO15 bleibt `INPUT_PULLUP`; TWAI-TX liegt auf
  Dummy-GPIO48.
- Hardware-Passivität und Verdrahtung müssen vor einem Fahrzeuganschluss
  geprüft werden. Bei Auffälligkeiten sofort STOP oder USB trennen.

## CEM-Firmware und Web-GUI

Die CEM-Firmware unterstützt:

- feste 500 kbit/s, Listen-Only
- expliziten START/STOP, keinen Auto-Start
- Dummy-TX-Schutz
- Zwei-Zyklus-Assistent mit Live-EIN/AUS-Anzeige der Kandidatenbits
- Bind-Auswahl pro Kandidat

Details: `OBD-CEM-Bus/docs/STAND_2026-11-06.md`,
`OBD-CEM-Bus/docs/SICHERHEIT_CAN_500.md`.

## OBD-Low-Bus

Das ältere Projekt enthält die passive Analyse des OBD-Diagnosebusses,
Signal-Kandidaten (z. B. Fahrstufe, Fußbremse, Rückfahrkamera) und die
zugehörigen Tools. Die Rohdaten bleiben privat.

## Bauen und testen

```bash
cd OBD-CEM-Bus/firmware
pio run -e esp32s3
pio test -e native

cd ../..
python -m unittest discover -s OBD-CEM-Bus/tests -p "test_*.py"
python OBD-CEM-Bus/tools/check_safety.py
python OBD-CEM-Bus/tools/check_hardware_pins.py
```

Für das OBD-Low-Bus-Projekt liegen die Befehle in
`OBD-Low-Bus/README.md`.

## Start unter Windows

Für das CEM-Projekt gibt es im Unterordner die Startskripte. Der lokale
Server läuft auf `http://127.0.0.1:8765/`; die Firmware wird über USB-CDC
angesprochen.

## Lizenz

**MIT-Lizenz** – siehe [`LICENSE`](LICENSE). Copyright (c) 2026 **lukas-ad**.

## Hinweis

Dieses Projekt steht in keiner Verbindung zu Volvo Cars. Alle Angaben zu
CAN-IDs und Signalen sind Analyseergebnisse und keine offiziellen
Herstellerdaten.
