# Sicherheitsstatus CEM-CAN - fester 500-kbit/s-Listen-Only-Betrieb

Stand: 2026-11-06

## Verbindlicher Status

- **Fahrzeug-CAN:** read-only Live-Test am 2026-11-06 durchgeführt.
  Hardware-Passivität ist weiterhin **nicht messtechnisch nachgewiesen**.
- **Kein CAN-Senden, kein Bitratenscan.** Nur 500 kbit/s, LISTEN_ONLY.
- **Firmware:** Boot = CAN aus, fester Testbetrieb **500 kbit/s**,
  ausschliesslich `TWAI_MODE_LISTEN_ONLY`, kein Senden.
- **START ist freigegeben** (`kAllowCanStart=true`), aber **kein Auto-Start**
  in der Firmware. Der Start erfolgt explizit über Desktop-Knopf, Browser oder API.
- **Kein Auto-Neuversuch** nach Bus-Off oder Installationsfehler.
- **Demo-Modus** erzeugt nur synthetische Frames und deaktiviert CAN.
- Details: `docs/STAND_2026-11-06.md`.

## Nachgewiesener Laufzeitstatus

- Firmware kompiliert und per COM8/USB aufgespielt (Hash verifiziert).
- Letzter Live-Lauf: **289.647 Frames**, **24 IDs**, **0 CAN-Fehler**,
  **33 USB-Queue-Drops**, TWAI **RUNNING**.
- Danach **CAN STOP**; lokaler Server beendet, COM8 freigegeben.
- Desktop-Knopf: `%USERPROFILE%\Desktop\Volvo CAN Live.lnk`.
- Kein Bitratenscan, kein CAN-Senden, kein Auto-Neuversuch.

## Auswertung der 500-kbit/s-Logs

Quelle: `messungen/session_20261105-210307_raw.jsonl` und `.csv`
(Test vom 05.11.2026, 20:19:48-20:23:01 UTC).

| Pruefung | Ergebnis |
|---|---|
| Frame-Events | **159.617** |
| Demo-/Testdaten | **0** (`demo=false`, `source=serial`) |
| Parse-Fehler | **0** |
| CAN-IDs | **24**, alle Standard-11-Bit |
| DLC | 8 (152.894), 4 (3.667), 3 (3.056) |
| Datenlaenge/Polsterung | alle DLC<8-Frames nur mit Null-Padding; keine Korruption |
| Sequenz | Segment 0: 130.090 Frames, lueckenlos seq 1..130.090; Segment 2: 29.519 Frames, 34 USB-Drops |
| Rate | ca. **870 Frames/s**; max. 10 s: **8.728** (ESP-Timestamp) bzw. **8.856** (Host-Zeit) |
| 8.735 Frames/10 s | **plausibel** (Fenstergrenze/Zeitbasis; innerhalb 8.728-8.856) |
| Top-IDs | 0x25, 0x27, 0x2A, 0x30, 0x33, 0x35, 0x3A, 0x40, 0x50, 0x85, 0x130, 0x57F |
| Fehler | keine `BUS_ERROR`/`BUS_OFF`-Meldungen in den Logs; `txerr=0`, `dropped=0` im Hauptsegment |

Die 125/250-kbit/s-Nullmessungen sind in diesem Log nicht dokumentiert; sie
stammen aus der frueheren Beobachtung. Der 500-kbit/s-Empfang selbst ist
durch echte, periodische CAN-Frames mit plausiblen IDs/DLC/Daten belegt.

**Bewertung:** 500 kbit/s ist durch die Empfangsdaten **plausibel bestaetigt**,
aber nicht metrologisch hart bewiesen (keine vollstaendigen TWAI-Fehlerzaehler,
kein Oszilloskop, keine zweite Gegenprobe). Die neue Firmware ist deshalb fest
auf 500 kbit/s eingestellt; der read-only START ist freigegeben.

## Verdacht: alte Bitratenwechsel als Stoerursache

Der alte Stand (Backup `ESP_Firmware_CEM_20261105-190050`) wechselte die
Bitrate ueber `switchSource()`:

- `can_manager.cpp`: `switchSource()` rief bei jedem Wechsel zuerst
  `uninstallTwai()` und dann `installTwai()` auf.
- `uninstallTwai()` setzte den TX-Pin nicht auf `INPUT_PULLUP`.
- `installTwai()` liess den IDF-Treiber den TX-GPIO als Ausgang konfigurieren;
  die Errata-Korrektur greift erst beim `twai_start()` (REC=128), nicht
  zwangslaeufig beim GPIO-Init.
- `taskLoop()` startete bei Bus-Off und nach Installationsfehlern automatisch
  alle 5 s neu.

Damit sind bei jedem Bitratenwechsel mehrere TWAI-Initialisierungen moeglich.
Ein kurzer dominanter Impuls auf TXD beim GPIO-/Treiber-Init ist dokumentiert
und wird von der Listen-Only-Errata-Korrektur nicht abgedeckt. Das ist die
konkrete verdaechtige Codestelle; ein Oszilloskopnachweis am Fahrzeugbus steht
noch aus.

## Korrigierte Sicherheitsprobleme

- Boot = CAN aus; kein automatischer TWAI-Install.
- Fester 500-kbit/s-Betrieb; nur `{500}` zugelassen; kein Scan.
- START ist freigegeben, aber kein automatischer Start in der Firmware.
- Kein Auto-Neuversuch nach Bus-Off/Installationsfehler.
- Echter CAN-TXD **GPIO15** bleibt immer `INPUT_PULLUP`; TWAI-TX geht auf
  **Dummy-GPIO48**. Damit kann der TWAI-Controller den Transceiver nicht
  dominant treiben, auch nicht bei einem Init-Glitch.
- STOP setzt GPIO15 auf `INPUT_PULLUP`, GPIO48 auf `INPUT`.
- Erweiterte TWAI-Statusausgabe mit `start_locked`, Alerts und Fehlerzaehlern.

## Schaltplanpruefung (Waveshare ESP32-S3-RS485-CAN)

- **U8: TJA1051T/3/1J**, High-Speed-CAN.
  - TXD (Pin 1) kommt vom Isolator U9 (VOA/TXD2').
  - RXD (Pin 4) geht zum Isolator U9 (VIE/RXD2').
  - S (Pin 8) liegt ueber R18 0R auf SGND: **Normal Mode, kein Silent/Standby**.
  - TXD hat laut NXP-Datenblatt einen internen Pull-up; HIGH = rezessiv.
- **U9: π163E31** Digitalisolator, Fail-Safe-Ausgang **HIGH**.
  - R35-R39 sind laut Schaltplan **NC**; offene Eingaenge ergeben HIGH.
  - TXD2' ist damit bei hochohmigem/hochgezogenem GPIO15 HIGH.
- **Boot:** GPIO15 hochohmig + Isolator-Fail-Safe HIGH + TJA1051-TXD-Pull-up
  ⇒ rezessiv. GPIO15 ist kein Strapping-Pin; der Pegel waehrend Reset/Bootloader
  ist trotzdem am realen Board mit dem Oszilloskop zu pruefen. GPIO48 (Dummy)
  wird erst beim TWAI-Install Ausgang.
- Der TJA1051 hat eine TXD-Dominant-Timeout-Schutzfunktion; sie verhindert
  Dauerdominant, aber **nicht** einen kurzen dominanten Init-Impuls.
- **Start (read-only Live-Test):** GPIO15 bleibt `INPUT_PULLUP`; TWAI-TX nur auf
  GPIO48; TXD bleibt HIGH ⇒ rezessiv. Der TWAI-Empfang laeuft ueber GPIO16.
- **Stop:** GPIO15 `INPUT_PULLUP`, GPIO48 `INPUT`; TXD HIGH ⇒ rezessiv.
- **Terminierung:** H1/R19 120 Ω; Jumperstellung und Bestueckung am realen
  Board pruefen. Standard soll offen sein; ein zusaetzlicher Abschluss kann
  den Bus belasten.

## Noch erforderliche Hardwarepruefungen

1. Sichtpruefung: Board vollstaendig vom Fahrzeug-CAN trennen; keine Stromdiebe.
2. 120-Ω-Jumper offen; zwischen CAN-H/L keine 120/60 Ω messen.
3. Durchgang GPIO15/16 zu U9/U8; GPIO48 freihalten (Dummy-TX).
4. Boot/Reset/STOP: GPIO15 hoch; U9-VOA/TXD2' hoch; U8-TXD hoch (Oszilloskop,
   auch waehrend Reset/Bootloader).
5. START nur am isolierten Bench-Testbus: TXD bleibt hoch, kein dominantes
   Signal, kein ACK/Error-Frame; TWAI-Init-Glitch messen.
6. Isolation/Common-Mode: CAN-GND-Konzept, isolierte 5-V/3,3-V-Versorgung,
   keine Masseschleife.
7. Fahrzeugbus-Abschluss mit Board: ca. 60 Ω, nicht ca. 40 Ω.
8. Kabelfarben, Stichlaenge, Verdrillung, Kontaktwiderstand.
9. Read-only Live-Test ist freigegeben (`kAllowCanStart=true`); nur 500 kbit/s,
   kurze Beobachtung, bei Auffaelligkeiten sofort STOP oder USB trennen.

## Freigabekriterien

Read-only Live-Test: **JA** (autorisiert am 2026-11-06). Die elektrische
Passivitaet und Verdrahtung sind weiterhin **NEIN/UNGEPRUEFT**; bei
Fahrzeugauffaelligkeiten sofort STOP oder USB trennen. Keine Dauerfreigabe fuer
andere Bitraten oder Sende Betrieb.
