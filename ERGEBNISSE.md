# Ergebnisse und Messdatenübersicht

## CEM-CAN

### Live-Aufzeichnungen 2026-11-06

- **500 kbit/s**, ausschließlich `LISTEN_ONLY`
- **24 Standard-11-Bit-IDs**, keine Extended-IDs auf diesem Abgriff
- Mehrere Live-Läufe mit insgesamt mehreren Millionen Frames
- Im normalen Empfang **0 Busfehler**
- Gegen Ende der Abendtests Busfehler während Bus-Schlaf-/Wake-Zyklen
  (192 bis 1.304 im laufenden Zähler); keine CAN-Sendung
- Aufzeichnungen mit getrennten Messdateien und Ereignismarkern

### Reproduzierte CEM-Zustände

`0x030` und `0x035` sind Zwillingsnachrichten: Bytes 1–7 identisch,
Byte 0 mit konstantem XOR `0x65`. Byte 0 ist ein Zähler/Integritätsfeld.

| Funktion | CAN-ID | Feld | AUS/anderer Zustand | EIN | Status |
|---|---|---|---|---|---|
| Licht AUS/Standlicht | `0x030`/`0x035` | Byte 2–3 | – | `7C61` | beobachtet |
| Wegbeleuchtung/Coming Home | `0x030`/`0x035` | Byte 2–3 | – | `7C60` | Kandidat |
| Abblendlicht | `0x030`/`0x035` | Byte 2–3 | – | `86 03` | praktisch bestätigt |
| Fernlicht manuell | `0x030`/`0x035` | Byte 2–3 | – | `92 2B` | praktisch bestätigt |
| Fernlicht Automatik/Nacht | `0x030`/`0x035` | Byte 2–3 | – | `92 6B` | praktisch bestätigt |
| Fernlicht weitere Basis | `0x030`/`0x035` | Byte 2–3 | – | `92 4B` | beobachtet |
| Fernlicht generisch | `0x030`/`0x035` | Byte 2–3 | – | Maske `0x9008` | Kandidat |
| Lichthupe | `0x030`/`0x035` | Byte 2–3 | – | `7C69` | bei Abblendlicht AUS bestätigt |

Weitere, nicht mehr aktive Lichtvarianten: `85A3`, `86 43`, `85C3`, `91EB` und
`92 0B`. Sie sind im GUI-Archiv, aber nicht als aktuelle Zustände bestätigt.

### Blinker

| Funktion | CAN-ID | Feld | Wert |
|---|---|---|---|
| Blinker links Befehl | `0x040` | Byte 5, Bit 4 | 0/1 |
| Blinker rechts Befehl | `0x040` | Byte 5, Bit 5 | 0/1 |
| Warnblinker Befehl | `0x040` | Byte 5, Bits 4+5 | beide 1 |
| Blinkstatus normal | `0x050` | Byte 4–7 | `01 90 01 90` |
| Warnblinkerstatus | `0x050` | Byte 4–7 | `01 F4 01 2C` |

`0x040` Byte 5 enthält zusätzlich stark flatternde Zählerbits (Bit 2 und 6);
diese sind nicht der Blinker.

### Wegbeleuchtung / Busruhe

- Während der Wegbeleuchtung bleibt `0x030/0x035` auf `7C60`.
- Beim Bus-Schlaf/Wake erscheinen `0x531` (`31 40 00 …`) und `0x532`
  (`32 40 00 …`); wahrscheinlich Network-Management-/Wake-Frames.
- Ein expliziter Ein-/Ausschaltbefehl für die Wegbeleuchtung war in den
  bisherigen Aufzeichnungen nicht sichtbar.
- Der Bus fiel mehrfach für etwa 17–71 Sekunden in Ruhe und wachte danach
  wieder auf; ein sauberer 90-Sekunden-Zyklus mit Befehl steht noch aus.

### Nicht auf diesem Abgriff gefunden

- Bremspedal
- Fahrstufe N/R
- separate Wegbeleuchtungs-Trigger-Nachricht

Die Referenzen `0x1FFF00A0` (Fahrstufe), `0x1FFF0200` (Fußbremse) und
`0x1FFF0144` (Rückfahrkamera) gehören zum OBD-Low-Bus und wurden auf dem
CEM-11-Bit-Bus nicht gesehen.

## Werkzeuge und Tests

- Lokaler Diagnoseserver mit Live-Monitor, Assistent, Bit-Test und Signalanalyse
- A/B-Analyse mit Mehrbyte-Feldern, Bitmatrix, Zeitdiagramm und Export
- Messungsverwaltung mit eigenen Namen und getrennten CSV-Dateien
- Umfangreiche Python-Tests und statische GUI-/Sicherheitsprüfungen
- Keine CAN-Sendefunktion im Projekt

## Hardware und Sicherheit

- Waveshare ESP32-S3-RS485-CAN, TJA1051 + Digitalisolator
- CAN TX GPIO15, RX GPIO16
- Echter TXD GPIO15 bleibt `INPUT_PULLUP`; TWAI-TX auf Dummy-GPIO48
- Nur LISTEN_ONLY; kein `twai_transmit`
- Errata-Workaround aktiv
- Kein Auto-Start, kein Auto-Neuversuch, kein Bitratenscan
- 120-Ω-Jumper, Verkabelung und Isolator/TXD sind noch messtechnisch zu prüfen

## Reproduzierbarkeit

Die vollständigen Rohdaten liegen lokal im Messordner. Öffentlich dokumentiert
sind Zählwerte, IDs, Zustände und allgemeine Ergebnisse.

```bash
cd OBD-CEM-Bus/firmware
pio run -e esp32s3
pio test -e native

cd ../..
python -m unittest discover -s OBD-CEM-Bus/tests -p "test_*.py"
python OBD-CEM-Bus/tools/check_local_safety.py
python OBD-CEM-Bus/tools/check_local_web.py
```
