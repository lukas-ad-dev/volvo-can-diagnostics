# Ergebnisse und Messdaten-Übersicht

## CEM-CAN

### Loganalyse 2026-11-05

- Quelle: 500-kbit/s-Aufzeichnung, Rohdaten nicht veröffentlicht.
- **159.617 Frames**
- **24 Standard-11-Bit-IDs**
- DLC: 8 Byte (152.894), 4 Byte (3.667), 3 Byte (3.056)
- Keine Demo-/Testdaten, keine Parse-Fehler
- Maximal **8.728–8.856 Frames pro 10 s** (Zeitbasis/Fenstergrenze)
- Top-IDs: `0x025`, `0x027`, `0x02A`, `0x030`, `0x033`, `0x035`,
  `0x03A`, `0x040`, `0x050`, `0x085`, `0x130`, `0x57F`

Die 8.735 Frames/10 s sind damit plausibel; die exakte Zahl hängt von der
Fenstergrenze ab.

### Live-Lauf 2026-11-06

- **289.647 Frames**, **24 IDs**
- **0 CAN-/Bus-/TX-/RX-Fehler**
- 33 USB-Queue-Drops (keine CAN-Fehler)
- TWAI **RUNNING**, danach **STOP**
- 500 kbit/s, LISTEN_ONLY

### CEM-Signale

Noch **keine bestätigten CEM-Decoder**. Der Assistent zeigte bei
„standlicht“ 0 Kandidaten, weil in beiden EIN-Zyklen kein Bit stabil
wechselte. Für den nächsten Test eine sicher schaltbare Aktion verwenden
(z. B. Fernlicht oder Rückwärtsgang) und die zwei Zyklen exakt einhalten.

## OBD-Low-Bus

Diese Ergebnisse sind **Referenz/Kandidaten**, keine CEM-Bestätigung:

| Signal | CAN-ID | Byte/Bit | Status |
|---|---|---|---|
| Fahrstufe P/R/N/D | `0x1FFF00A0` | Byte 6, Bits 0–1 | Kandidat |
| Fußbremse | `0x1FFF0200` | Byte 4, Bit 1 | Kandidat |
| Rückfahrkamera | `0x1FFF0144` | Byte 2, Bit 3, aktiv bei 0 | Kandidat |
| Abblendlicht/Fernlicht | – | – | auf OBD-Bus nicht stabil sichtbar |
| Standlicht/Parkbremse | – | – | auf OBD-Bus nicht stabil sichtbar |
| Türen/Fenster/Spiegel/Sitz | – | – | keine neuen IDs/Bits beobachtet |

## Hardware und Sicherheit

- Waveshare ESP32-S3-RS485-CAN, TJA1051 + π163E31
- CAN TX GPIO15, RX GPIO16
- Echter TXD GPIO15 bleibt `INPUT_PULLUP`; TWAI-TX auf Dummy-GPIO48
- Nur LISTEN_ONLY; kein `twai_transmit`
- Errata-Workaround aktiv
- Kein Auto-Start, kein Auto-Neuversuch
- 120-Ω-Jumper, Verkabelung und Isolator/TXD sind noch messtechnisch zu prüfen

## Reproduzierbarkeit

Die vollständigen Rohdaten bleiben privat. Öffentlich dokumentiert sind
Zählwerte, IDs, DLC-Verteilung und allgemeine Ergebnisse. Für eigene
Messungen:

```bash
cd OBD-CEM-Bus/firmware
pio run -e esp32s3
pio test -e native

cd ../..
python -m unittest discover -s OBD-CEM-Bus/tests -p "test_*.py"
python OBD-CEM-Bus/tools/check_safety.py
```
