# Volvo CAN Control - OBD-Low-Bus

Passive CAN-Diagnose für den OBD-Diagnosebus eines Volvo V90 T8 (SPA, MJ 2021)
mit dem Waveshare Industrial ESP32-S3-RS485-CAN.

**Sicherheit:** ausschließlich LISTEN_ONLY, kein CAN-Senden, keine
Diagnoseanfragen, keine Gateway-Manipulation, keine Steuergerätecodierung.
GPIO1/GPIO2 bleiben hochohmig und deaktiviert. Kein 12-V-Anschluss.

Der Ordnername `OBD-Low-Bus` ist eine organisatorische Bezeichnung. Bus-Typ
und Bitrate sind nicht abschließend bestätigt; 500 kbit/s ist der
voreingestellte, unverifizierte Standardwert.

## Start unter Windows

1. USB-C-Datenkabel vom Laptop zum Waveshare.
2. Im Projektordner `start_obd_low.bat` starten.
3. Der Starter erkennt COM8/den ESP-Port, startet den lokalen Server auf
   `http://127.0.0.1:8765` und öffnet die Oberfläche.
4. Das Profil wird als `OBD-Low-Bus` angezeigt.

Es darf immer nur ein Profil gleichzeitig laufen. `start_obd_cem.bat` und
`start_obd_low.bat` verweigern den Start, wenn bereits das andere Profil auf
Port 8765 läuft.

## Identifizierte Signale (Kandidaten)

| Signal | CAN-ID | Byte | Bit/Maske | Aktivwert |
|---|---|---|---|---|
| Fahrstufe P | 0x1FFF00A0 | 6 | Maske 0x03 | 0x00 |
| Fahrstufe R | 0x1FFF00A0 | 6 | Maske 0x03 | 0x01 |
| Fahrstufe N | 0x1FFF00A0 | 6 | Maske 0x03 | 0x02 |
| Fahrstufe D | 0x1FFF00A0 | 6 | Maske 0x03 | 0x03 |
| Fußbremse | 0x1FFF0200 | 4 | Bit 1 / 0x02 | 0x02 |
| Rückfahrkamera/Rückansicht | 0x1FFF0144 | 2 | Bit 3 / 0x08 | 0x00 |

Diese Signale wurden am 04.11.2026 praktisch geprüft, sind im Projekt aber
weiterhin als **Kandidaten** geführt. Die formale Bestätigung mit drei
unabhängigen Gegenproben ist noch nicht abgeschlossen.

Licht, Parkbremse, manuelle 360-Grad-Kamera sowie Türen/Verriegelung/Fenster/
Sitz/Spiegel/Kofferraum waren auf dem beobachteten OBD-Diagnosebus nicht
sichtbar (Gateway-/Body-CAN-/LIN-Effekt).

## Struktur

- `firmware/` - PlatformIO-Firmware, Pins, Partitionen
- `web/` - Firmware-Weboberfläche als Quelldateien
- `local_web/` - lokale Windows-Diagnoseoberfläche
- `tools/` - USB-Logger, lokaler Server, Signal-Engine, Checks
- `config/` - Laufzeit-Signaldefinitionen
- `decoder/` - Referenzarchiv der Decoder/Kandidaten
- `tests/` - native C++-Tests und Python-Tests
- `docs/` - Architektur, Messungen und Signalerkennung
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

- `docs/HARDWARE.md`
- `docs/MESSUNGEN_20261104.md`
- `docs/SIGNALERKENNUNG.md`
- `docs/CAN_ANALYSE.md`
- `docs/CAN_REFERENZEN.md`
- `docs/ARCHITEKTUR.md`
- `docs/ROADMAP.md`
