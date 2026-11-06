# Ergebnisse

## CEM-CAN

Ich habe den internen CEM-Bus mehrfach mit 500 kbit/s aufgezeichnet, immer
nur passiv. Auf dem Abgriff sind 24 Standard-IDs mit 11 Bit sichtbar,
Extended-IDs waren nicht dabei. Während des normalen Empfangs gab es keine
Busfehler. Fehler traten erst auf, als der Bus in den Schlaf ging und wieder
aufwachte.

### Lichtzustände

`0x030` und `0x035` sind Zwillingsnachrichten. Die Bytes 1 bis 7 sind gleich,
Byte 0 unterscheidet sich immer um XOR `0x65`. Byte 0 ist ein Zähler- und
Integritätsfeld und kein Schaltsignal.

| Funktion | CAN-ID | Feld | Zustand | Stand |
|---|---|---|---|---|
| Licht aus / Standlicht | `0x030` / `0x035` | Byte 2-3 | `7C61` | beobachtet |
| Wegbeleuchtung / Coming Home | `0x030` / `0x035` | Byte 2-3 | `7C60` | Kandidat |
| Abblendlicht | `0x030` / `0x035` | Byte 2-3 | `86 03` | im Test bestätigt |
| Fernlicht manuell | `0x030` / `0x035` | Byte 2-3 | `92 2B` | im Test bestätigt |
| Fernlicht Automatik/Nacht | `0x030` / `0x035` | Byte 2-3 | `92 6B` | im Test bestätigt |
| Fernlicht weitere Basis | `0x030` / `0x035` | Byte 2-3 | `92 4B` | beobachtet |
| Fernlicht generisch | `0x030` / `0x035` | Byte 2-3 | Maske `0x9008` | Kandidat |
| Lichthupe | `0x030` / `0x035` | Byte 2-3 | `7C69` | bei Abblendlicht aus bestätigt |

Ältere Varianten wie `85A3`, `86 43`, `85C3`, `91EB` und `92 0B` liegen im
Archiv der Oberfläche. Sie sind nicht als aktuelle Zustände bestätigt.

### Blinker

| Funktion | CAN-ID | Feld | Wert |
|---|---|---|---|
| Blinker links | `0x040` | Byte 5, Bit 4 | 0/1 |
| Blinker rechts | `0x040` | Byte 5, Bit 5 | 0/1 |
| Warnblinker | `0x040` | Byte 5, Bits 4+5 | beide 1 |
| Blinkstatus normal | `0x050` | Byte 4-7 | `01 90 01 90` |
| Warnblinkerstatus | `0x050` | Byte 4-7 | `01 F4 01 2C` |

In `0x040` Byte 5 wechseln die Bits 2 und 6 sehr schnell. Das sind
Zählerbits und nicht der Blinker. Für die Blinker sind nur Bit 4 und Bit 5
brauchbar.

### Wegbeleuchtung und Busruhe

Während der Wegbeleuchtung bleibt `0x030`/`0x035` auf `7C60`. Beim Aufwachen
des Busses erscheinen `0x531` (`31 40 ...`) und `0x532` (`32 40 ...`).
Wahrscheinlich sind das Network-Management-Frames. Einen klaren Ein- oder
Ausschaltbefehl für die Wegbeleuchtung habe ich nicht gesehen.

Der Bus war in den Aufzeichnungen mehrfach für 17 bis 71 Sekunden ruhig. Ein
vollständiger 90-Sekunden-Zyklus mit sichtbarem Befehl fehlt noch.

### Nicht auf diesem Bus gefunden

Bremspedal und Fahrstufe N/R waren auf dem CEM-11-Bit-Bus nicht als stabile
Zustände zu sehen. Die bekannten Referenzen `0x1FFF00A0` (Fahrstufe),
`0x1FFF0200` (Fußbremse) und `0x1FFF0144` (Rückfahrkamera) gehören zum
OBD-Low-Bus.

## Werkzeuge

- Lokaler Server mit Live-Monitor, Prüfablauf, Bit-Test und Signalanalyse
- A/B-Auswertung mit Mehrbyte-Feldern, Bitmatrix, Zeitdiagramm und Export
- Messungen mit eigenem Namen und getrennten CSV-Dateien
- Python-Tests und statische Prüfungen für Oberfläche und Sicherheit
- Keine CAN-Sendefunktion

## Hardware und Sicherheit

- Waveshare ESP32-S3-RS485-CAN mit TJA1051 und Digitalisolator
- CAN TX auf GPIO15, RX auf GPIO16
- Echter TXD bleibt `INPUT_PULLUP`, TWAI-TX nutzt Dummy-GPIO48
- Nur `LISTEN_ONLY`, kein `twai_transmit`
- Errata-Workaround aktiv
- Kein Auto-Start, kein Auto-Neuversuch, kein Bitratenscan
- 120-Ohm-Jumper, Verkabelung und Isolator sind noch zu prüfen

## Nachvollziehen

Die Rohdaten liegen lokal im Messordner. Im Repository stehen nur Zählwerte,
IDs, Zustände und allgemeine Ergebnisse.

```bash
cd OBD-CEM-Bus/firmware
pio run -e esp32s3
pio test -e native

cd ../..
python -m unittest discover -s OBD-CEM-Bus/tests -p "test_*.py"
python OBD-CEM-Bus/tools/check_local_safety.py
python OBD-CEM-Bus/tools/check_local_web.py
```
