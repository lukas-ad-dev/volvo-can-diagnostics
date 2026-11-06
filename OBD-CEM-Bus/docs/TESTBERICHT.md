# Testbericht OBD-CEM-Bus

Stand: 2026-11-05

## Umfang

Das CEM-Projekt ist eine eigenstaendige Kopie der OBD-Low-Bus-Software mit
CEM-spezifischer Konfiguration, Profil und Dokumentation. Es wurden auf dem
MGMT-Core **keine Hardware geflasht** und **keine Fahrzeugverbindung**
hergestellt. Es liegen noch keine CEM-Messungen vor.

## Firmware-Build

- PlatformIO Core 6.2.0, `espressif32@8.0.0`, Arduino Core 3.3.12
- Ergebnis: **SUCCESS**
- RAM: 58,4 % (191.524 / 327.680 Bytes)
- Flash: 30,2 % (1.266.467 / 4.194.304 Bytes)
- CEM-Firmware nutzt denselben Waveshare-Code und denselben CAN-Pin-Satz
  (TX=GPIO15, RX=GPIO16, RS485 17/18).

## Native C++-Tests

- `pio test -e native` mit `test_dir = ../tests`
- Ergebnis: **9 von 9 bestanden**

## Python-Tests

- `python3 -m unittest discover -s tests -v`
- Ergebnis: **30 von 30 bestanden**
- Enthalten: USB-Logger-PTY, lokaler HTTP-Server, Demo, Export,
  Signal-Engine, A/B-Assistent, Sicherheitslogik

## Statische Checks

- `check_board_config.py`: OK
- `check_hardware_pins.py`: OK
- `check_safety.py`: OK (nur LISTEN_ONLY, kein Senden)
- `check_local_safety.py`: OK
- `check_web.py`: OK
- `check_local_web.py`: OK (85 HTML-IDs, 71 JS-IDs, 15 API-Pfade)

## Demo-/Profil-Smoke-Test

- Demo-Server mit Profil `OBD-CEM-Bus`: 22 Signale, Demo-Frames, UI HTTP 200
- CSV-Export: Header korrekt; JSON-Export: Liste korrekt
- Profil-Sperre: Start von `OBD-Low-Bus` auf demselben Port wurde abgewiesen
- Decoder-Ladefunktion: 22 Signale; alle Fahrzeugdecoder Status `unknown`;
  nur `can_bus_active` (System) ist `confirmed`
- Zielsignale `vehicle_awake` und `driver_door` sind vorhanden
- Keine Hardware geflasht, kein Fahrzeug angeschlossen

## Bewertung

Die CEM-Software ist baubar, testbar und startbar. Die eigentliche
CEM-Signalidentifikation ist **nicht** durchgefuehrt, weil dafuer zuerst
der physische CAN-Standard, die Pinbelegung und die Bitrate am Fahrzeug
verifiziert werden muessen.

## Offene Punkte

- Physischer CAN-Standard des CEM-Busses (High-Speed vs. Low-Speed
  Fault-Tolerant) unbekannt.
- CEM-Pinbelegung, Kabelfarben, Terminierung und Bitrate unbekannt.
- Keine CEM-Messungen.
- Keine CEM-Decoder bestaetigt.
- Kein Fahrzeuganschluss ohne Hardwarefreigabe.
