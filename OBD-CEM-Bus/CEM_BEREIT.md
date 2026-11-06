# CEM-CAN – Bereitstellung & Sicherung (2026-11-06)

## Verbindlicher Sicherheitsstatus

- **Fahrzeug-CAN:** read-only Live-Test wurde am 2026-11-06 durchgeführt.
  Hardware-Passivität ist weiterhin **nicht messtechnisch nachgewiesen**.
- **Kein CAN-Senden, kein Bitratenscan.** Nur 500 kbit/s, LISTEN_ONLY.
- **Boot = CAN aus (STOP)**; `START` ist für den read-only Live-Test freigegeben
  (`kAllowCanStart=true`), aber **kein Auto-Start** in der Firmware.
- **Fester Testbetrieb 500 kbit/s**, nur `TWAI_MODE_LISTEN_ONLY`.
- **TWAI-TX = Dummy-GPIO48**; echter CAN-TXD GPIO15 bleibt `INPUT_PULLUP`.
- Details: `docs/STAND_2026-11-06.md` und `docs/SICHERHEIT_CAN_500.md`.

## Status

- **Firmware-Build:** SUCCESS (`esp32s3`, 2026-11-06)
- **Aufgespielt:** JA (COM8, nur USB)
- **Letzter Live-Lauf:** **289.647 Frames**, **24 IDs**, **0 CAN-Fehler**,
  33 USB-Queue-Drops; TWAI **RUNNING**, danach **STOP**
- **START:** freigegeben (`kAllowCanStart=true`), nur explizit per Knopf/API
- **Desktop-Knopf:** `%USERPROFILE%\Desktop\Volvo CAN Live.lnk`
- **Native Tests:** 9/9 PASSED
- **Python-Tests:** 30 OK, 1 skipped
- **Sicherheitschecks:** alle OK
- **CAN-Modus:** `TWAI_MODE_LISTEN_ONLY` (kein Senden)
- **Ausgänge:** GPIO1/GPIO2 hochohmig (`INPUT`), nicht angesteuert
- **Bitrate:** fest 500 kbit/s (durch 289.647 Frames bestätigt)
- **Fahrzeugdecoder:** keine auf CEM bestätigt (nur System-Busstatus)
- **Signale:** 12 Zielsignale vorbereitet, Status **UNBEKANNT**

## Build-Ergebnis

- `firmware/.pio/build/esp32s3/firmware.bin` (1,3 MB)
- `firmware/.pio/build/esp32s3/bootloader.bin`
- `firmware/.pio/build/esp32s3/partitions.bin`
- `firmware/.pio/build/esp32s3/firmware.elf` / `firmware.map` (Debug)
- SHA-256 `firmware.bin`: `7EBEF8878E324D96EBA1ECF7B958E5E6C2946C05F095F03C915D89B6749C6116`

**Hinweis:** Die `firmware.bin` enthält die kompilierten Zugangsdaten aus
`include/secrets.h` (WLAN-AP). Sie ist **nicht** für die Weitergabe bestimmt.

## Flashen (nur USB, CAN getrennt)

USB-C anschließen, seriellen Port anpassen:

```bash
pio run -e esp32s3 -t upload --upload-port COM8
```

Danach seriellen Monitor mit 115200 Baud öffnen. USB-CDC ist aktiv.
Nach dem Boot muss `STATUS` `CAN=STOP`, `Bitrate=500 kbit/s` und
`START=FREI` melden. Der Start erfolgt ausschließlich explizit über den
Desktop-Knopf, den Browser-Button oder die API.

## Vor dem Fahrzeuganschluss zwingend lesen

- `docs/STAND_2026-11-06.md` (letzter funktionierender Stand)
- `docs/SICHERHEIT_CAN_500.md` (verbindlich)
- `docs/HARDWARE_CEM.md`
- `docs/SIGNALZIELE.md`

Kernpunkte:
- Boot = `STOP`; `START` ist freigegeben, aber kein Auto-Start in der Firmware.
- Fester 500-kbit/s-Betrieb; kein Bitratenscan, kein Auto-Neuversuch.
- Waveshare **TJA1051** = High-Speed-CAN (ISO 11898-2); S-Pin liegt auf GND (Normal Mode).
- Der physikalische Standard des CEM-Busses ist **nicht geklärt**. Kein
  Anschluss an einen möglichen Low-Speed-Fault-Tolerant-Bus.
- Kabelfarben (Grau/Braun, Gelb/Lila) sind **vorläufig** und am konkreten
  Fahrzeug zu verifizieren.
- 120-Ohm-Terminierung am Waveshare bleibt **deaktiviert** (NC) und ist vor
  dem Anschluss zu messen.
- **Nur passiv empfangen.** Kein Senden, keine Diagnose, keine Codierung.
- **Keine Fahrzeug-CAN-Netze miteinander verbinden.**
- Hardware-Passivität ist **nicht** nachgewiesen; bei Fahrzeugauffälligkeiten
  sofort STOP oder USB trennen.

## Tests (lokal am 2026-11-06 ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `pio run -e esp32s3` | SUCCESS |
| `pio run -e esp32s3 -t upload --upload-port COM8` | SUCCESS (Hash verifiziert) |
| Laufzeit `STATUS` / `TWAI` per USB | `CAN=STOP`, 500 kbit/s, `START=FREI` |
| Live-Test | 289.647 Frames, 24 IDs, 0 CAN-Fehler, TWAI RUNNING |
| `pio test -e native` | 9/9 PASSED |
| `python -m unittest discover -s tests` | 30 OK, 1 skipped |
| `tools/check_safety.py` | OK (Warnung: START freigegeben) |
| `tools/check_local_safety.py` | OK (5 Python-Dateien) |
| `tools/check_hardware_pins.py` | OK (CAN TX=15 nur INPUT_PULLUP, RX=16; TWAI-TX=Dummy 48; RS485 17/18) |
| `tools/check_board_config.py` | OK (16 MB Flash, OPI-PSRAM, USB-CDC) |
| `tools/check_local_web.py` | OK |
| `tools/check_web.py` | OK |

**Nicht ausgeführt:** Bitratenscan, CAN-Serverstart. Der letzte Fahrzeugtest war
ein autorisierter read-only 500-kbit/s-Lauf; die Hardware-Passivität ist
weiterhin nicht messtechnisch nachgewiesen.

## DoIP-Diagnose-Übergabe

Die Windows-DoIP-/UDS-Messwerte und die KfzDiagnose-App liegen im Ordner
`UEBERGABE_WINDOWS_DIAGNOSE_2026-11-05/` (siehe dortige `README_UEBERGABE.md`).

**DoIP ist nicht CAN:** ECU-Adressen sind Logical Addresses, keine CAN-IDs.

## Backups

Siehe `../backups/README.md` (Volvo-Root).

## Offene Punkte

1. Hardware-Passivität nach `docs/SICHERHEIT_CAN_500.md` prüfen (Terminierung, TXD-Ruhepegel, Isolator/TJA1051, Isolation, Abgriff, Busabschluss).
2. Physikalischen CAN-Standard des CEM-Busses klären (High-Speed vs. Low-Speed FT).
3. Kabelfarben und Abgriffpunkt am konkreten V90 T8 MJ2021 verifizieren.
4. 500-kbit/s-Empfang ist bestätigt; 12 Zielsignale per A/B-Vergleich identifizieren.
5. Keine IDs/Bitmasken erfinden; Decoder erst nach mehrfacher Gegenprobe bestätigen.
6. Ursache der früheren Fahrzeugstörung per Oszilloskop eingrenzen (TWAI-Init/TXD, Terminierung, Abgriff).
7. START ist für den read-only Live-Test freigegeben (`kAllowCanStart=true`); Hardware-Passivität weiterhin offen.
8. CSV-Logger des lokalen Servers reparieren; bis dahin vollständige RAW-Daten bzw. USB-Logger nutzen.
9. Assistenten-Zwei-Zyklus-Test mit einer sicher schaltbaren Aktion wiederholen; der letzte „standlicht“-Lauf hatte 0 stabile Bitwechsel.
