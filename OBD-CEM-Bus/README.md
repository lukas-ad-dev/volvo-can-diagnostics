# Volvo CAN Control - OBD-CEM-Bus

Passive CAN-Analyse des internen CEM-CAN-Busses eines Volvo V90 T8
(SPA-Plattform, Modelljahr 2021) mit dem Waveshare Industrial
ESP32-S3-RS485-CAN.

**Sicherheit:** ausschließlich LISTEN_ONLY. Kein CAN-Senden, keine
Diagnoseanfragen, keine Nachrichteninjektion, keine Gateway-Manipulation,
keine Steuergerätecodierung. GPIO1/GPIO2 bleiben hochohmig und deaktiviert.

## Status

- **500 kbit/s**, LISTEN_ONLY, Boot = STOP, START nur explizit.
- Live-Test: 289.647 Frames, 24 Standard-IDs, 0 CAN-Fehler.
- Noch keine bestätigten CEM-Decoder; Kandidaten werden live angezeigt.
- Dummy-TX auf GPIO48, echter CAN-TXD GPIO15 bleibt `INPUT_PULLUP`.

## Zielsignale

Alle zunächst **UNBEKANNT**:

- Rückwärtsgang und Fahrgeschwindigkeit
- Abblendlicht, Fernlicht, Standlicht
- Parkkamera und Rangiermodus
- Ver-/Entriegelung und Fahrertür
- Zündung, Komfort/Radio, Fahrzeug wach/Ruhezustand

## Start unter Windows

1. Board per USB anschließen (COM8).
2. Desktop-Knopf **Volvo CAN Live** starten.
3. Server öffnet `http://127.0.0.1:8765/`; CAN wird explizit gestartet.
4. **CAN STOP** im Browser beendet den Empfang sofort.
5. Bei Problemen den letzten Stand in `docs/STAND_2026-11-06.md` lesen.

## Assistent und Bit-Test

- Der Assistent arbeitet mit einem Aktionszyklus:
  10 s AUS, Aktion EIN markieren, 10 s aufnehmen, auswerten.
- Kandidaten zeigen live `EIN/AUS`; Zielauswahl pro Kandidat wird beim
  Binden übernommen.
- Der **Bit-Test** nimmt bis zu 60 Bits auf, die sich während des
  Testbetriebs ändern; dauerhaft konstante Bits werden ausgeblendet.
  Jedes Bit kann live beobachtet und frei benannt werden.

## Struktur

- `firmware/` - PlatformIO-Firmware
- `web/` - Firmware-Weboberfläche
- `local_web/` - lokale Windows-Diagnoseoberfläche
- `tools/` - USB-Logger, lokaler Server, Signal-Engine, Checks
- `config/` - CEM-Signaldefinitionen
- `decoder/` - Referenzdecoder, unverifiziert
- `tests/` - native und Python-Tests
- `docs/` - Hardware, Sicherheit, Architektur und CEM-Test
- `messungen/` - lokale Messdateien

## Bauen und testen

```bash
cd firmware
pio run -e esp32s3
pio test -e native

cd ..
python -m unittest discover -s tests -v
python tools/check_safety.py
python tools/check_hardware_pins.py
python tools/check_board_config.py
```

`firmware/include/secrets.h` enthält die lokalen WLAN-Zugangsdaten. Als Vorlage
dient `firmware/include/secrets.example.h`.

## Dokumentation

- `docs/HARDWARE_CEM.md`
- `docs/SIGNALZIELE.md`
- `docs/HARDWARE.md`
- `docs/SIGNALERKENNUNG.md`
- `docs/CAN_ANALYSE.md`
- `docs/ARCHITEKTUR.md`
- `docs/STAND_2026-11-06.md`
- `docs/SICHERHEIT_CAN_500.md`
