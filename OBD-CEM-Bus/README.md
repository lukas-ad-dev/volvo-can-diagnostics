# Volvo CAN Control - OBD-CEM-Bus

Passive CAN-Analyse des internen CEM-CAN-Busses eines Volvo V90 T8
(SPA-Plattform, Modelljahr 2021) mit dem Waveshare Industrial
ESP32-S3-RS485-CAN.

**Sicherheit:** ausschliesslich LISTEN_ONLY. Kein CAN-Senden, keine
Diagnoseanfragen, keine Nachrichteninjektion, keine Gateway-Manipulation,
keine Steuergeraetecodierung. GPIO1/GPIO2 bleiben hochohmig und deaktiviert.

> **Aktueller Status (2026-11-06):** Read-only Live-Test mit **289.647 Frames**,
> **24 IDs**, **0 CAN-Fehlern** und TWAI **RUNNING** durchgeführt. Firmware:
> Boot = `STOP`, fester Testbetrieb **500 kbit/s**, echter CAN-TXD GPIO15 bleibt
> `INPUT_PULLUP`, TWAI-TX liegt auf Dummy-GPIO48. `START` ist freigegeben, aber
> kein Auto-Start in der Firmware.
>
> **Desktop-Knopf:** `%USERPROFILE%\Desktop\Volvo CAN Live.lnk` startet Server,
> CAN-START (LISTEN_ONLY) und Browser. Letzter Stand zum Lesen:
> `docs/STAND_2026-11-06.md`. Hardware-Passivität ist weiterhin nicht
> messtechnisch nachgewiesen; bei Auffälligkeiten sofort STOP/USB trennen.

## Status

- Es sind **noch keine Fahrzeugdecoder fuer den CEM-CAN bestaetigt**.
- Die Decoder aus dem OBD-Low-Bus-Projekt sind als **Referenz** kopiert und
  in `config/signals.json` sowie `decoder/` als `UNVERIFIZIERT AUF CEM`
  gekennzeichnet.
- Die vorhandenen CAN-IDs und Bitmasken sind Suchhypothesen, keine CEM-Nachweise.
- Der physische CAN-Standard (High-Speed vs. Low-Speed Fault-Tolerant) und
  die Bitrate des CEM-Busses sind noch nicht bestaetigt.

## Zielsignale (alle zunaechst UNBEKANNT)

Manövrierleuchten:
- Rueckwaertsgang aktiv
- Fahrgeschwindigkeit km/h (numerisch)
- Abblendlicht aktiv
- Fernlicht aktiv
- Parkkamera/Rangiermodus aktiv

Ambientebeleuchtung:
- Fahrzeug entriegelt
- Fahrzeug von aussen verriegelt
- Fahrertuer geoeffnet
- Zuendungsstatus
- Komfortbetrieb/Radio aktiv
- Fahrzeug wach
- Fahrzeug im Ruhezustand

## Start unter Windows

1. Board per USB anschließen (COM8). Fahrzeug-CAN nur im autorisierten
   read-only Test; Hardware-Passivität bleibt zu prüfen.
2. Auf dem Desktop **`Volvo CAN Live.lnk`** doppelklicken.
   Der Knopf startet den lokalen Server, wartet auf COM8, sendet **einmalig
   START** (500 kbit/s, LISTEN_ONLY) und öffnet
   `http://127.0.0.1:8765/`.
3. Im Browser Frames, TWAI-Status und Assistent beobachten. **CAN STOP** im
   Browser beendet den Empfang sofort.
4. Nur ein Profil gleichzeitig auf Port 8765. Bei Problemen den letzten Stand
   in `docs/STAND_2026-11-06.md` und `SAVE_20261106-0042/README_SAVE.md` lesen.

## GitHub

Das lokale Git-Repository ist vorbereitet. Eine einfache Schritt-für-Schritt-
Anleitung für GitHub ohne Vorkenntnisse steht in `docs/GITHUB_START.md`.
Empfohlen: **privates** Repository; Secrets, Rohdaten, `.venv`, `.pio` und
`SAVE_*` werden nicht hochgeladen.

## Struktur

- `firmware/` - PlatformIO-Firmware (Waveshare ESP32-S3-RS485-CAN)
- `web/` - Firmware-Weboberflaeche
- `local_web/` - lokale Windows-Diagnoseoberflaeche
- `tools/` - USB-Logger, lokaler Server, Signal-Engine, Checks
- `config/` - CEM-Signaldefinitionen (Referenzen, Status unbekannt)
- `decoder/` - Referenzdecoder, ausdruecklich UNVERIFIZIERT AUF CEM
- `tests/` - native und Python-Tests
- `docs/` - CEM-Hardware, Signalziele, Architektur, Testbericht
- `messungen/` - noch leer; OBD-Referenzmessungen liegen im Low-Projekt

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

`firmware/include/secrets.h` ist lokal und wird nicht in Archive aufgenommen.
Die CEM-Firmware nutzt standardmaessig den AP-Namen `Volvo-CEM-CAN`.

## Dokumentation

- `docs/HARDWARE_CEM.md`
- `docs/SIGNALZIELE.md`
- `docs/MESSUNGEN_CEM.md`
- `docs/INSTALLATION.md`
- `docs/HARDWARE.md`
- `docs/SIGNALERKENNUNG.md`
- `docs/CAN_ANALYSE.md`
- `docs/ARCHITEKTUR.md`
- `docs/TESTBERICHT.md`
- `PROJEKTUEBERSICHT.md`

---

## Private Windows-Diagnose

Private DoIP-, VIN-, Screenshot- und Fahrzeugdaten sind **nicht** Teil dieses
oeffentlichen Repos.

## Bereitstellung (2026-11-05)

- `CEM_BEREIT.md` – Build-/Teststatus, Firmware-Binary, Flash-Beispiel,
  Sicherheitshinweise.
- Firmware-Binary: `firmware/build/firmware.bin` (nicht weitergeben;
  enthaelt kompilierte Secrets).
- Backups: siehe `../backups/README.md`.
- Sicherheit: `../SECURITY_HINWEIS_2026-11-05.md`.
- DoIP-Diagnose-Uebergabe: `UEBERGABE_WINDOWS_DIAGNOSE_2026-11-05/`.
