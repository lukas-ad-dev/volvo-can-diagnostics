# Sicherheitsstatus CEM-CAN – fester 125-kbit/s-Listen-Only-Betrieb

> **Historisch/ueberholt (2026-11-05):** Die ausgewerteten Logs belegen
> 500 kbit/s. Aktuell gilt `SICHERHEIT_CAN_500.md`; die 125-kbit/s-Angaben in
> diesem Dokument sind nicht mehr der aktive Testbetrieb.

Stand: 2026-11-05

## Verbindlicher Status

- **Fahrzeug-CAN:** nicht freigegeben. Der Waveshare bleibt vom Fahrzeug-CAN getrennt.
- **Keine CAN-Tests** und kein automatischer Bitratenscan, bis die Hardwareprüfungen
  abgeschlossen und ausdrücklich freigegeben sind.
- **Kein CAN-Server/CAN-Scanner** starten. Der alte lokale Server wurde gestoppt.
- **Firmware:** Boot = CAN aus (`STOP`), fester Testbetrieb **125 kbit/s**,
  ausschließlich `TWAI_MODE_LISTEN_ONLY`, kein Senden.
- **Start nur explizit** per USB-Befehl `START`; `STOP` deinstalliert den TWAI-Treiber
  und hält CAN-TXD (GPIO15) auf `INPUT_PULLUP`.
- **Demo-Modus** erzeugt nur synthetische Frames und deaktiviert CAN.

## Zwischenfall

Beim früheren automatischen Bitratenscan meldete der Volvo Störungen an
Blinkleuchten/Beleuchtung. Nach Trennen der USB-Versorgung verschwanden die
Meldungen nach ca. 20–30 s. Der Scan ergab bei 500 kbit/s 8735 Frames in 10 s;
bei anderen Raten traten Busfehler auf. Dieser Befund ist **keine Freigabe** für
500 kbit/s und wird nicht wiederholt.

Mögliche Ursachen der Störung, die vor einem neuen Fahrzeuganschluss geprüft
werden müssen:

- unerkannte 120-Ohm-Terminierung auf dem Waveshare (zusätzlicher dritter Abschluss),
- langer/unsauberer Stichabgriff oder Stromdieb-Kontaktprobleme,
- Transceiver-/Isolator-Verhalten während Reset oder Treiberwechsel,
- unbestätigte Pin-/Transceiver-Zuordnung,
- fehlende/common-mode-Referenz bei nicht angeschlossenem GND.

## Nachgewiesene Punkte (Software/Board)

| Punkt | Status | Nachweis |
|---|---|---|
| Firmware kompiliert | JA | `pio run -e esp32s3` SUCCESS |
| Native Tests | JA | 9/9 PASSED |
| Python-Tests | JA | 30 OK (1 skipped) |
| Aufgespielt | JA | COM8, esptool Hash verifiziert; CAN-Seite nicht verifiziert |
| Boot = CAN aus | JA | Laufzeit `STATUS`: `CAN=STOP`; `TWAI`: Treiber nicht installiert |
| Feste Bitrate 125 | JA | Laufzeit `STATUS`: `Bitrate=125 kbit/s` |
| Nur Listen-Only | JA | Quellcode + Sicherheitscheck |
| Kein Senden | JA | kein `twai_transmit`; Sicherheitscheck OK |
| Errata-Workaround | JA | `CONFIG_TWAI_ERRATA_FIX_LISTEN_ONLY_DOM 1` im verwendeten `qio_opi`-SDK |
| GPIO-Zuordnung | JA (Software) | CAN TX=15, RX=16; RS485 TX=17, RX=18; DE=21 |
| Hardware-Passivität | NEIN/UNGEPRÜFT | nur messtechnisch/visuell prüfbar |
| Fahrzeugfreigabe | NEIN | Hardware-Passivität nicht nachgewiesen |

## Noch erforderliche Hardwareprüfungen

### Vor jedem Fahrzeuganschluss

1. **Sichtprüfung:** Waveshare vollständig vom Fahrzeug-CAN trennen. Keine
   Stromdiebe, keine offenen Litzen, keine Verbindung zum OBD-Low-Bus.
2. **Terminierung:** 120-Ohm-Jumper am Waveshare muss **offen** sein. Zwischen
   CAN-H und CAN-L am Board darf **keine** 120 Ohm (bzw. 60 Ohm) messbar sein.
3. **Pin-/Transceiver-Zuordnung:** Durchgang von ESP32 GPIO15/16 zum
   Transceiver-TXD/RXD prüfen; keine unbeabsichtigte Verbindung zum RS485-Teil.
   Schaltplan/Board-Revision dokumentieren.
4. **TXD-Ruhezustand:** Im Boot- und STOP-Zustand muss TXD rezessiv (hoch) sein.
   GPIO15 ist `INPUT_PULLUP`; zusätzlichen Pull-up im Isolator-/Transceiver-Pfad
   laut Schaltplan verifizieren.
5. **Versorgung/Isolation:** Isolierten DC-DC und digitale Isolation prüfen.
   CAN-GND nur nach Schaltplanfreigabe verbinden; keine Masseschleife erzeugen.
6. **Leitung/Abgriff:** Verdrillung, Stichlänge und Kontaktwiderstand der
   Stromdiebe messen. Kein langer Stich; keine Unterbrechung des Fahrzeugbusses.
7. **Busabschluss im Fahrzeug:** Bei ausgeschalteter Zündung CAN-H gegen CAN-L
   messen. Mit angeschlossenem Board muss der Wert dem Fahrzeugzustand
   entsprechen (typisch ca. 60 Ohm); ein Abfall auf ca. 40 Ohm zeigt eine
   zusätzliche Terminierung an.
8. **Bench-Test ohne Fahrzeug:** Nur mit einem separaten 125-kbit/s-Testbus und
   zweitem Knoten. Mit Oszilloskop prüfen: keine dominanten Pegel vom Waveshare,
   kein ACK, keine Error Frames; `TX` bleibt rezessiv.
9. **Strom-/Spannungsmessung:** Ruhestrom und 5-V/3,3-V-Versorgung prüfen;
   keine Rückwirkung auf den Testbus.

### Erst danach

10. Fahrzeuganschluss nur nach dokumentierter Freigabe durch den Nutzer.
11. Erster Fahrzeugtest ausschließlich mit `START` an 125 kbit/s, kurzer
    Beobachtung, sofortigem `STOP` bei Auffälligkeiten und ohne Bitratenwechsel.
12. Bei Fahrzeugstörungen: USB sofort trennen, `STOP` dokumentieren, keine
    Wiederholung ohne neue Hardwareprüfung.

## Bedienung

- `STATUS` – zeigt `CAN=STOP/ARMED`, Bitrate und Modus, startet nichts.
- `TWAI` – zeigt Treiberstatus/Alerts, startet nichts.
- `START` – startet **125 kbit/s** Listen-Only (nur nach Freigabe).
- `STOP` – stoppt und deinstalliert den Treiber, TXD auf Pull-up.

Manuelles PowerShell-Werkzeug: `tools/can_start.ps1` (kein Autostart; `START`
erfordert zusätzlich `-ConfirmSafety`).

## Freigabekriterien

Eine Fahrzeugfreigabe ist erst möglich, wenn alle Punkte 1–9 dokumentiert
bestanden sind und die Hardware-Passivität messtechnisch belegt ist. Bis dahin
gilt: **kein Fahrzeuganschluss, keine CAN-Tests, kein Serverstart.**
