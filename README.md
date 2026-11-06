# Volvo CAN Diagnostics – CEM & OBD Low Bus

Passive CAN-Analyse für einen **Volvo V90 T8 (SPA-Plattform, Modelljahr 2021)**
mit dem Waveshare **ESP32-S3-RS485-CAN**. Das Projekt dokumentiert zwei
CAN-Busse und die Werkzeuge, mit denen die Nachrichten gelesen und
ausgewertet werden.

## Fahrzeug und Busse

| Bereich | Beschreibung |
|---|---|
| Fahrzeug | Volvo V90 T8, SPA, Modelljahr 2021 |
| OBD-Diagnosebus | OBD2 Pin 6/14, älterer Analysepfad |
| CEM-CAN | interner CAN-Bus hinter dem Fahrerfach |
| Bitrate CEM | 500 kbit/s (durch Live-Messung bestätigt) |
| Betriebsart | ausschließlich LISTEN_ONLY, kein Senden |

## Ziel

Die Signale des Fahrzeugs sollen passiv identifiziert und dokumentiert werden:

- Rückwärtsgang und Fahrgeschwindigkeit
- Abblendlicht, Fernlicht, Standlicht
- Parkkamera und Rangiermodus
- Ver- und Entriegelung, Fahrertür
- Zündung, Komfort/Radio, Fahrzeug wach/Ruhezustand

Das Projekt sendet keine CAN-Nachrichten, stellt keine Diagnoseanfragen und
verändert keine Steuergeräte.

## Hardware

Für den Aufbau werden benötigt:

- Waveshare **ESP32-S3-RS485-CAN**
- USB-C-Datenkabel zum Laptop
- CAN-H/CAN-L-Anschluss am Fahrzeug oder OBD2-Pigtail (Pin 6/14)
- optional: kurze, verdrillte CAN-Leitung
- Multimeter für Durchgang, Spannung und Widerstand

Die 120-Ω-Terminierung des Boards bleibt standardmäßig deaktiviert und wird
vor dem Fahrzeuganschluss geprüft. CAN TX liegt auf GPIO15, CAN RX auf GPIO16.
Der echte TXD bleibt im Firmware-Betrieb hochgezogen; TWAI-TX nutzt einen
Dummy-Pin.

## Projekte

| Ordner | Inhalt |
|---|---|
| `OBD-CEM-Bus/` | Firmware, Web-GUI, Zwei-Zyklus-Assistent, CEM-Dokumentation |
| `OBD-Low-Bus/` | passive OBD-Analyse, Signalkandidaten, Logger und Tools |

## Bisherige Ergebnisse

- **CEM-CAN:** 500 kbit/s, 24 Standard-IDs, Live-Lauf mit 289.647 Frames,
  0 CAN-Fehler, TWAI RUNNING.
- **CEM-Decoder:** noch keine bestätigten Signale; der Assistent zeigt
  Kandidatenbits live als EIN/AUS.
- **OBD-Low-Bus:** Fahrstufe P/R/N/D (`0x1FFF00A0`, Byte 6, Bits 0–1),
  Fußbremse (`0x1FFF0200`, Byte 4, Bit 1) und Rückfahrkamera
  (`0x1FFF0144`, Byte 2, Bit 3) als Kandidaten.
- **Assistent:** zwei Aktionszyklen (AUS → EIN → AUS → EIN), Live-Anzeige
  der Kandidatenbits und Binden an eine Zielkachel.

Details stehen in [`PROJEKTVERLAUF.md`](PROJEKTVERLAUF.md) und
[`ERGEBNISSE.md`](ERGEBNISSE.md).

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

Die Befehle für das OBD-Low-Bus-Projekt stehen in `OBD-Low-Bus/README.md`.

## Start unter Windows

Die CEM-Firmware wird über USB-CDC angesprochen. Der lokale Diagnoseserver
läuft auf `http://127.0.0.1:8765/`. Startskripte und weitere Hinweise liegen
im jeweiligen Projektordner.

## Dokumentation

- [`PROJEKTVERLAUF.md`](PROJEKTVERLAUF.md) – Fahrzeug, Ziel, Zeitlinie und
  bisherige Entwicklung
- [`ERGEBNISSE.md`](ERGEBNISSE.md) – Messwerte, CAN-IDs und Signalkandidaten
- `OBD-CEM-Bus/docs/` – Hardware, Sicherheit, Architektur und CEM-Test
- `OBD-Low-Bus/docs/` – OBD-Messungen und Signalerkennung

## Lizenz

**MIT-Lizenz** – siehe [`LICENSE`](LICENSE). Copyright (c) 2026 **lukas-ad**.

## Hinweis

Dieses Projekt steht in keiner Verbindung zu Volvo Cars. CAN-IDs und
Signalangaben sind eigene Analyseergebnisse und keine offiziellen
Herstellerdaten.
