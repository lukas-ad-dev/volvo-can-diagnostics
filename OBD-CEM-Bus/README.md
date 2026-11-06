# Volvo CAN Control - OBD-CEM-Bus

Passive CAN-Analyse des internen CEM-CAN-Busses eines Volvo V90 T8
(SPA-Plattform, Modelljahr 2021) mit dem Waveshare Industrial
ESP32-S3-RS485-CAN.

**Sicherheit:** ausschließlich `LISTEN_ONLY`. Kein CAN-Senden, keine
Diagnoseanfragen, keine Nachrichteninjektion, keine Gateway-Manipulation,
keine Steuergerätecodierung. Echter TXD bleibt hochohmig; TWAI-TX nutzt einen
Dummy-Pin.

## Status 2026-11-06

- **500 kbit/s**, Boot = STOP, START nur explizit
- **24 Standard-11-Bit-IDs**
- Live-Aufzeichnungen mit mehreren Millionen Frames
- Im normalen Empfang 0 Busfehler; Fehler nur im Umfeld von Bus-Schlaf/Wake
- Kein Auto-Start, kein Auto-Neuversuch, kein Bitratenscan

### Erkannte Zustände

- `0x030`/`0x035` sind Zwillingsnachrichten; Byte 0 ist Zähler/Integrität.
- Abblendlicht: `86 03` (praktisch bestätigt)
- Fernlicht manuell: `92 2B`; Automatik/Nacht: `92 6B`; weitere Basis: `92 4B`
- Fernlicht generisch: Byte 2-3, Maske `0x9008` (Byte 2 Bit 7+4, Byte 3 Bit 3)
- Lichthupe: `7C69` (bisher bei Abblendlicht AUS)
- Wegbeleuchtung/Coming Home: `7C60` (Kandidat; Trigger nicht gefunden)
- Blinker links/rechts: `0x040` Byte 5 Bit 4/5; Warnblinker beide Bits
- Blinkstatus: `0x050` Byte 4-7 `01 90 01 90`; Warnblinker `01 F4 01 2C`

Nicht auf diesem CEM-11-Bit-Bus gefunden: Bremspedal und Fahrstufe N/R. Diese
Referenzen liegen im OBD-Low-Bus-Bereich (`0x1FFF...`).

## Oberfläche

- Live-CAN-Monitor mit ID-Filter und Ausblenden von Dauersignalen
- Pruefablauf mit einem Aktionszyklus
- Bit-Test bis 60 ändernde Bits
- Signalanalyse mit A/B-Vergleich, Bitmatrix, Zeitdiagramm und Export
- Kompakte Signal-Karten, Details per Klick, Archiv für Altkandidaten
- Messungsverwaltung mit eigenen Namen und getrennten CSV-Dateien

## Start unter Windows

1. Board per USB anschließen.
2. Startskript bzw. Desktop-Knopf **Volvo CAN Live** starten.
3. Server öffnet `http://127.0.0.1:8765/`; CAN wird explizit gestartet.
4. **CAN STOP** beendet den Empfang sofort.
5. Bei Problemen den letzten Stand in `docs/STAND_2026-11-06.md` lesen.

## Struktur

- `firmware/` - PlatformIO-Firmware
- `web/` - Firmware-Weboberfläche
- `local_web/` - lokale Windows-Diagnoseoberfläche
- `tools/` - USB-Logger, lokaler Server, Signal-Engine, Checks
- `config/` - CEM-Signaldefinitionen
- `decoder/` - Referenzdecoder, unverifiziert
- `tests/` - native und Python-Tests
- `docs/` - Hardware, Sicherheit, Architektur und CEM-Test

## Bauen und testen

```bash
cd firmware
pio run -e esp32s3
pio test -e native

cd ..
python -m unittest discover -s tests -v
python tools/check_local_safety.py
python tools/check_local_web.py
```

## Dokumentation

- `docs/HARDWARE_CEM.md`
- `docs/SIGNALZIELE.md`
- `docs/SIGNALERKENNUNG.md`
- `docs/CAN_ANALYSE.md`
- `docs/ARCHITEKTUR.md`
- `docs/SICHERHEIT_CAN_500.md`
- `docs/STAND_2026-11-06.md`

## Hinweis

Keine Verbindung zu Volvo Cars. Alle CAN-IDs und Zustände sind eigene
Analyseergebnisse. Arbeiten am Fahrzeug nur bei sicherem Stand und mit
passender Hardware; die Verantwortung liegt beim Betreiber.
