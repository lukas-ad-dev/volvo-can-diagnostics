# Volvo CAN Control - OBD-Low-Bus

Passive CAN-Diagnose fuer den OBD-Diagnosebus eines Volvo V90 T8 (SPA, MJ 2021)
mit dem Waveshare Industrial ESP32-S3-RS485-CAN.

**Sicherheit:** ausschliesslich LISTEN_ONLY, kein CAN-Senden, keine
Diagnoseanfragen, keine Gateway-Manipulation, keine Steuergeraetecodierung.
GPIO1/GPIO2 bleiben hochohmig und deaktiviert. Kein 12-V-Anschluss.

Der Ordnername `OBD-Low-Bus` ist eine organisatorische Bezeichnung. Bus-Typ
und Bitrate sind nicht abschliessend bestaetigt; 500 kbit/s ist nur der
voreingestellte, unverifizierte Standardwert.

## Start unter Windows

1. USB-C-Datenkabel vom Laptop zum Waveshare.
2. Im Projektordner `start_obd_low.bat` starten.
   - Alternativ `start_volvo_can_control.bat`.
   - Demo: `start_diagnose.bat --demo`.
   - USB-Logger: `start_logger.bat`.
3. Der Starter erkennt COM8/den ESP-Port, startet den lokalen Server auf
   `http://127.0.0.1:8765` und oeffnet die Oberflaeche.
4. Das Profil wird in der Oberflaeche als `OBD-Low-Bus` angezeigt.

Es darf immer nur ein Profil gleichzeitig laufen. `start_obd_cem.bat` und
`start_obd_low.bat` verweigern den Start, wenn bereits das andere Profil auf
Port 8765 laeuft.

## Identifizierte Signale (Kandidaten)

| Signal | CAN-ID | Byte | Bit/Maske | Aktivwert |
|---|---|---|---|---|
| Fahrstufe P | 0x1FFF00A0 | 6 | Maske 0x03 | 0x00 |
| Fahrstufe R | 0x1FFF00A0 | 6 | Maske 0x03 | 0x01 |
| Fahrstufe N | 0x1FFF00A0 | 6 | Maske 0x03 | 0x02 |
| Fahrstufe D | 0x1FFF00A0 | 6 | Maske 0x03 | 0x03 |
| Fussbremse | 0x1FFF0200 | 4 | Bit 1 / 0x02 | 0x02 |
| Rueckfahrkamera/Rueckansicht | 0x1FFF0144 | 2 | Bit 3 / 0x08 | 0x00 |

Diese Signale wurden am 04.11.2026 praktisch geprueft, sind im Projekt aber
weiterhin als **Kandidaten** gefuehrt. Die formale Bestaetigung mit drei
unabhaengigen Gegenproben ist noch nicht abgeschlossen.

Licht, Parkbremse, manuelle 360-Grad-Kamera sowie Tueren/Verriegelung/Fenster/
Sitz/Spiegel/Kofferraum waren auf dem beobachteten OBD-Diagnosebus nicht
sichtbar (Gateway-/Body-CAN-/LIN-Effekt).

## Struktur

- `firmware/` - PlatformIO-Firmware, Pins, Partitionen, Secrets
- `web/` - Firmware-Weboberflaeche als Quelldateien
- `local_web/` - lokale Windows-Diagnoseoberflaeche
- `tools/` - USB-Logger, lokaler Server, Signal-Engine, Checks
- `config/` - Laufzeit-Signaldefinitionen
- `decoder/` - Referenzarchiv der Decoder/Kandidaten
- `tests/` - native C++-Tests und Python-Tests
- `docs/` - Architektur, Messanleitungen und Signalerkennung
- `messungen/` - lokale Messdateien

## Bauen und testen

```bash
cd firmware
pio run -e esp32s3
pio test -e native
cd ..
python3 -m unittest discover -s tests -v
python3 tools/check_safety.py
python3 tools/check_hardware_pins.py
python3 tools/check_board_config.py
python3 tools/check_web.py
python3 tools/check_local_web.py
```

`firmware/include/secrets.h` enthält die lokalen WLAN-Zugangsdaten. Als Vorlage
dient `firmware/include/secrets.example.h`.

## Dokumentation

- `docs/HARDWARE.md`
- `docs/MESSUNGEN_20261104.md`
- `docs/SIGNALERKENNUNG.md`
- `docs/CAN_ANALYSE.md`
- `docs/CAN_REFERENZEN.md`
- `docs/ARCHITEKTUR.md`
- `docs/ROADMAP.md`
- `docs/MESSUNGEN_20261104.md`
- `docs/WINDOWS_IMPORT_2026-11-05.md`
- `docs/WINDOWS_VS_SERVER_DIFF.md`
- `PROJEKTUEBERSICHT.md`
