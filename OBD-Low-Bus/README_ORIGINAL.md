# Volvo CAN Control

**Version 0.1 – passive CAN-Analyse für einen Volvo V90 T8 (SPA-Plattform)**

Dieses Projekt ist eine erste, vollstaendig lauffaehige Basis fuer die passive Beobachtung und Aufzeichnung von CAN-Nachrichten mit einem Waveshare Industrial ESP32-S3-RS485-CAN. Es sendet **niemals** CAN-Nachrichten, stellt keine Diagnoseanfragen und steuert keine Fahrzeugfunktionen.

> **Wichtig:** Die Firmware wurde am 04.11.2026 auf das angeschlossene Waveshare-Board geflasht und ueber USB-CDC getestet. **Es wurde noch kein Fahrzeug angeschlossen.** Die tatsaechliche CAN-Bitrate des Fahrzeugs ist nicht bestaetigt; 500 kbit/s ist nur der voreingestellte, ausdruecklich unverifizierte Standardwert.

## Sicherheit zuerst

- TWAI ist ausschliesslich im Modus `TWAI_MODE_LISTEN_ONLY` konfiguriert.
- Es gibt keinen Aufruf von `twai_transmit`, keine Diagnoseanfragen und kein Replay.
- Listen-Only erzeugt keine Bestaetigungsframes (ACK) und beeinflusst den Bus nicht aktiv.
- GPIO1/GPIO2 bleiben in V0.1 hochohmig (INPUT), werden nicht angesteuert und sind nicht ueber die API schaltbar. Ein LOW-Pegel koennte ein LOW-aktives Relais einschalten; deshalb wird bewusst kein Pegel getrieben.
- Kein automatischer Deep Sleep. CAN-Stille wird nicht als Fahrzeug-Ruhezustand interpretiert.
- Die 120-Ohm-CAN-Terminierung des Boards ist laut Hersteller standardmaessig NC und muss fuer eine Stichleitung deaktiviert bleiben. Die tatsaechliche Jumper-Stellung vor dem Anschluss pruefen.
- Nur fuer rechtmaessige, autorisierte Diagnose am eigenen Fahrzeug verwenden. Nicht waehrend der Fahrt anschliessen.

## Hardwarebelegung (verifiziert am 04.11.2026)

- **CAN (TWAI):** TX = **GPIO15**, RX = **GPIO16**
- **RS485:** TX = **GPIO17**, RX = **GPIO18** (von dieser Firmware nicht verwendet)
- **Ausgaenge:** GPIO1/GPIO2, hochohmig und gesperrt

Die Belegung liegt zentral in `lib/volvo_core/include/volvo_core/hardware_pins.h`; `static_asserts` und `tools/check_hardware_pins.py` verhindern versehentliche Aenderungen.

> **Korrektur:** Die fruehere Annahme CAN TX=GPIO17/RX=GPIO18 war falsch. Der offizielle Waveshare-Schaltplan und das Demo-Header `WS_GPIO.h` belegen CAN TXD2=IO15/RXD2=IO16 sowie RS485 TXD1=IO17/RXD1=IO18. Die Firmware wurde am 04.11.2026 auf die bestaetigte 15/16-Belegung korrigiert. Details in `HARDWARE.md`.

## Funktionsumfang V0.1

- WLAN-Access-Point `Volvo-CAN-Control`, WPA2, Standard-IP `192.168.4.1`, Webserver auf Port 80.
- Deutsches, responsives Dark-Dashboard mit Dashboard, CAN-Livemonitor, Signalvergleich, Aufzeichnung/Export und Einstellungen.
- CAN-Empfang ueber TWAI, nur lesend, Bitrate 125/250/500 kbit/s umschaltbar.
- Live-Anzeige mit Zeitstempel, ID (Hex), Standard/Extended, DLC, Datenbytes, Empfangshaeufigkeit, Filter, Pause, Loeschen, Ausblenden und Sortieren.
- Signalvergleich mit zwei Messphasen A/B: neue IDs, verschwundene IDs, geaenderte Bytes/Bits, Variabilitaet und Frequenzaenderungen. Keine automatische Bedeutungszuweisung.
- Ringpuffer im PSRAM (16.384 Frames), dokumentierte Verwurfzaehler, CSV- und JSON-Export nach dem Stoppen.
- Zusaetzlicher NDJSON-Stream auf TCP-Port 81 fuer den Python-CSV-Collector unter Windows (lange Messungen).
- Demo-Modus mit synthetischen, ueberall als `DEMO` gekennzeichneten Frames. Demo-Daten werden niemals als echte Fahrzeugdaten ausgegeben.
- Vorbereitete Ausgangssteuerung fuer GPIO1/GPIO2, in V0.1 hochohmig und hart gesperrt.
- Vorbereitete Energiespararchitektur ohne automatischen Deep Sleep.

## Projektstruktur

```
Volvo/
├── platformio.ini              # ESP32-S3- und Native-Testumgebung
├── partitions.csv              # 16-MB-Flashlayout
├── include/
│   ├── app_config.h            # Pins, Puffer, Grenzen
│   ├── secrets.example.h       # Vorlage fuer WLAN-Passwort
│   └── secrets.h               # lokal, nicht einchecken
├── lib/volvo_core/             # reine C++-Logik ohne Arduino
│   └── include/volvo_core/     # CanFrame, Ringpuffer, Statistik, Phasen, Demo, CSV
├── src/                        # Firmware (Arduino, TWAI, Webserver, Stream)
├── web/                        # HTML/CSS/JS der Firmware-Oberflaeche
├── local_web/                  # HTML/CSS/JS der lokalen Windows-Signalerkennung
├── config/                     # Signale, bestaetigte Definitionen, Referenz-Hypothesen
├── tools/
│   ├── build_web.py            # erzeugt src/web_ui.cpp aus web/
│   ├── usb_can_logger.py       # Windows-USB-CDC-Logger
│   ├── local_can_diagnostics.py# lokaler HTTP-Server 127.0.0.1:8765
│   ├── volvo_can_control.py    # Desktop-Starter mit COM-Port-Erkennung
│   ├── signal_engine.py        # Signal-LEDs, Editor-Logik, Assistent, Bestaetigung
│   ├── compare_measurements.py # Messungsvergleich
│   ├── volvo_can_collector.py  # TCP-CSV-Collector
│   ├── generate_demo_data.py   # DEMO-Beispieldaten
│   ├── check_hardware_pins.py  # Pinbelegungs-Test
│   ├── check_board_config.py   # Flash-/PSRAM-Test
│   ├── check_safety.py         # statischer CAN-/Ausgangs-Sicherheitscheck
│   ├── check_local_safety.py   # Python-Sicherheitscheck
│   ├── check_web.py            # statischer Firmware-Webcheck
│   └── check_local_web.py      # statischer Check der lokalen Oberflaeche
├── test/
│   ├── test_core/              # Unity-Tests der reinen Logik
│   ├── test_collector.py       # TCP-Collector-Tests
│   ├── test_usb_logger.py      # USB-Logger inkl. PTY-Simulation
│   ├── test_compare.py         # Vergleichs-Tests
│   ├── test_signal_engine.py   # LED-, Bit-, Assistenten- und Bestaetigungstests
│   └── test_local_server.py    # HTTP-, Demo-, Editor-, Export- und Disconnect-Tests
├── data/demo/                  # synthetische DEMO-Frames
├── start_logger.bat            # Windows-Start fuer den USB-Logger
├── start_diagnose.bat          # Windows-Start fuer die lokale Signalerkennung
├── start_volvo_can_control.bat # Desktop-Starter (COM-Erkennung + Browser)
├── ERSTER_TEST.md              # Ablauf fuer den ersten Hardwaretest
├── ECHTE_CAN_MESSUNG.md        # erster OBD2-Anschluss Pin 6/14 + Gateway-Hinweise
├── SIGNALERKENNUNG.md          # Anleitung fuer die lokale Signalerkennung
├── CAN_REFERENZEN.md           # Quellen, Plattformtrennung, Hypothesen
└── docs/                       # Architektur und Testbericht
```

## Schnellstart (nur Demo, ohne Fahrzeug)

1. Projekt auf den Windows-Laptop uebertragen und in VS Code/PlatformIO oeffnen (siehe `INSTALLATION.md`).
2. `include/secrets.h` aus `include/secrets.example.h` erzeugen und ein eigenes WLAN-Passwort (mindestens 12 Zeichen) eintragen.
3. Firmware bauen und per USB flashen: `pio run -t upload`.
4. Mit dem WLAN `Volvo-CAN-Control` verbinden und `http://192.168.4.1` oeffnen.
5. In **Einstellungen** den **Demo-Modus** aktivieren. Alle Frames tragen dann sichtbar `DEMO`.
6. Im **Signalvergleich** Phase A starten, einige Sekunden warten, stoppen, Phase B starten, stoppen und vergleichen. Das Demo-Bit "Kamera" wechselt alle 15 Sekunden und erzeugt so einen sichtbaren Unterschied.
7. Fuer die lokale Signalerkennung auf dem Laptop `start_diagnose.bat --demo` ausfuehren und `http://127.0.0.1:8765` oeffnen; Details in `SIGNALERKENNUNG.md`.

## Dokumentation

- `INSTALLATION.md` – Windows, PlatformIO, Flashen, WLAN, USB-/TCP-Collector, Fahrzeuganschluss.
- `ERSTER_TEST.md` – konkreter Ablauf fuer den ersten Hardwaretest am 04.11.2026.
- `ECHTE_CAN_MESSUNG.md` – sichere Schritt-fuer-Schritt-Anleitung fuer den ersten OBD2-Anschluss (Pin 6/14) und den Umgang mit dem Volvo-Gateway.
- `SIGNALERKENNUNG.md` – lokale Oberflaeche, Signalkacheln, Editor, Assistent, Bestaetigung.
- `CAN_REFERENZEN.md` – recherchierte Quellen, Plattformtrennung P1/P2/SPA und unverifizierte Hypothesen.
- `HARDWARE.md` – Waveshare-Anschluesse, Pins, Terminierung, GPIO1/2, Sicherheit.
- `CAN_ANALYSE.md` – Vorgehen fuer Messphasen und die spaetere ID-Zuordnung.
- `ROADMAP.md` – geplante Entwicklungsstufen.
- `docs/ARCHITEKTUR.md` – Firmware-Aufbau, Datenfluss, API, Speicher.
- `docs/TESTBERICHT.md` – tatsaechlich ausgefuehrte Tests und Ergebnisse.

## Getesteter Stand (04.11.2026, Windows + reale Hardware)

- **Firmware-Build:** erfolgreich mit PlatformIO 6.2.0, `espressif32@8.0.0`, Arduino Core 3.3.12, ArduinoJson 7.4.3.
  - RAM: 58,4 % (191.524 von 327.680 Bytes), Flash: 30,2 % (1.266.479 von 4.194.304 Bytes der App-Partition).
- **Native C++-Tests:** 9 von 9 bestanden (inkl. Hardware-Pin- und USB-NDJSON-Test).
- **Python-Tests:** 30 ausgefuehrt, 29 bestanden, 1 uebersprungen (PTY-Test ist unter Windows nicht verfuegbar).
- **Sicherheitscheck:** bestanden (kein `twai_transmit`, kein `TWAI_MODE_NORMAL`, kein Deep Sleep, GPIO1/GPIO2 hochohmig und ungetrieben; Python-Werkzeuge ohne CAN-Sende-/Diagnosezugriff).
- **Weboberflaechen:** Firmware-UI und lokale Diagnose-UI: HTML/JS-ID-Abgleich, API-Pfad-Abgleich und JavaScript-Syntaxpruefung bestanden. Lokale UI um Live-CAN-Monitor mit Filtern, Raten, Aufzeichnung und CSV-Export erweitert.
- **Reale Hardware:** ESP32-S3 rev. v0.2 auf **COM8** erkannt (VID:PID 303A:1001), 16 MB Flash, 8 MB PSRAM bestaetigt; Firmware erfolgreich geflasht, Boot ueber USB-CDC gelesen, TWAI startet im LISTEN_ONLY-Modus mit 500 kbit/s, GPIO1/GPIO2 bleiben hochohmig.
- **Lokaler Server am echten ESP:** verbunden ueber COM8; ohne CAN-Bus erwartungsgemaess keine Frames, aber korrekte Status- und Fehleranzeige.
- **Demomodus:** 79 DEMO-Frames in 4 s, 4 IDs, 18 Nachrichten/s, Filter, 14 Signalkacheln (13 davon UNBEKANNT), CSV-Export und A/B-Assistent mit Kandidatenbindung getestet; Kandidat bleibt `candidate`.
- **Desktop-Starter:** Verknuepfung `Volvo CAN Control` angelegt und getestet; COM8 erkannt, Server auf 127.0.0.1:8765 gestartet, UI und `app.js` per HTTP erreichbar, Browser wurde geoeffnet.
- **Nicht getestet:** echter CAN-Bus am Fahrzeug, reale Bitrate/Terminierung, Volvo-Gateway-Verhalten, WLAN-AP-Bedienung der ESP-UI vom Laptop, echte CAN-Frames ueber USB-CDC ohne Bus, praktische Signalbestaetigung. Details in `docs/TESTBERICHT.md`.

## Rechtliches und Haftung

Das Projekt ist fuer die eigene, autorisierte Fahrzeugdiagnose gedacht. Der Anschluss an fremde Fahrzeuge, Manipulation, unbefugtes Auslesen oder Eingriffe in sicherheitsrelevante Systeme sind nicht erlaubt. Der Nutzer ist fuer die Einhaltung lokaler Gesetze und Herstellervorgaben selbst verantwortlich. Keine Gewaehr fuer die Richtigkeit abgeleiteter Signalzuordnungen.

## Laufender Diagnoseserver

Die Desktop-Verknuepfung startet den Server im Fenster `Volvo CAN Control`. Dieses Fenster muss offen bleiben (Minimieren ist ok), solange `http://127.0.0.1:8765` genutzt wird. Wird das Fenster geschlossen, endet der Server; ein erneuter Doppelklick auf die Verknuepfung startet ihn wieder. Der Server ist bewusst kein Windows-Dienst und laeuft nicht unsichtbar im Hintergrund.

