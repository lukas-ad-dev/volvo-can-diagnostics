# Testbericht

Stand: **04.11.2026**, Windows-Laptop mit angeschlossenem Waveshare ESP32-S3-RS485-CAN (COM8). Der urspruengliche Linux-Bericht vom 03.11.2026 wurde durch die tatsaechlich auf Windows und am realen Board ausgefuehrten Tests ersetzt. Nicht durchgefuehrte Tests sind am Ende ausdruecklich aufgefuehrt.

## Umgebung

- Windows 10/11, PowerShell 5.1
- Python 3.11.9, lokale virtuelle Umgebung `.venv`
- PlatformIO Core 6.2.0 (im Projekt-venv)
- Plattform `espressif32@8.0.0`
- Arduino Core 3.3.12
- ArduinoJson 7.4.3
- Unity 2.6.1
- MinGW-w64 / g++ 16.2.0 (nur native Tests)
- Node.js 24.17.0 (nur JavaScript-Syntaxpruefung)
- Waveshare ESP32-S3-RS485-CAN: ESP32-S3 rev. v0.2, 16 MB Flash, 8 MB eingebettetes PSRAM, MAC `28:84:85:B4:15:84`, VID:PID `303A:1001`

## 1. Firmware-Build

Befehl:

```powershell
.venv\Scripts\pio.exe run -e esp32s3
```

Ergebnis: **SUCCESS**

- RAM: 58,4 % (191.524 von 327.680 Bytes)
- Flash: 30,2 % (1.266.479 von 4.194.304 Bytes der 4-MB-App-Partition)
- Firmware: `.pio\build\esp32s3\firmware.bin` (ca. 1,3 MB)
- Keine Compilerfehler im finalen Build.
- PlatformIO bezeichnet das generische Board als "N8 (No PSRAM)"; das ist kosmetisch. `qio_opi` ist konfiguriert, und der reale Chip meldet 8 MB eingebettetes PSRAM.

## 2. Native C++-Tests

Befehl (MinGW im PATH):

```powershell
.venv\Scripts\pio.exe test -e native
```

Ergebnis: **9 von 9 bestanden**

- Ringpuffer: Ueberschreiben, Verwurfzaehler, Reihenfolge
- ID-Statistik: Zaehler, OR/AND-Variabilitaet, Frequenz
- Phasenvergleich: neue IDs, gemeinsame IDs, Byte-/Bit-Aenderung, Frequenz
- Phasenstart: parallele Phase wird abgelehnt
- Demo-Generator: alle Frames `demo=true`, gueltige IDs/DLC, Kamera-Bit wechselt
- Hardware-Pinbelegung: CAN TX=GPIO15, RX=GPIO16, RS485 TX=GPIO17, RX=GPIO18; keine Ueberschneidung
- USB-NDJSON-Format: type=can, Zeitstempel, ID, DLC, Daten, Demo-Kennzeichnung
- Ausgangssperre: kein Einschalten moeglich; Pins hochohmig
- CSV-Formatierung

## 3. Python-Tests

Befehl:

```powershell
.venv\Scripts\python.exe -m unittest discover -s test -v
```

Ergebnis: **30 Tests ausgefuehrt, 29 bestanden, 1 uebersprungen**

Der PTY-Integrationstest des USB-Loggers wird auf Windows uebersprungen, weil Windows keine Unix-PTY bereitstellt. Alle anderen Tests bestanden:

- NDJSON-Parsing (gueltig/ungueltig/fehlende Felder)
- CSV-Zeilen fuer Standard- und Extended-Frames
- TCP-Integrationstest: lokaler Testserver sendet drei Frames, Collector schreibt Header und drei CSV-Zeilen
- USB-Logger: NDJSON-Parsing, CSV-Zeilen, Szenario-Namen
- Messungsvergleich: neue IDs, geaenderte Bytes/Bits, Demo-Ausschluss
- Signal-Engine: LED-Zustaende, Timeout/UNKNOWN, Bitmasken, Invertierung, Little/Big Endian, Faktor/Offset, A/B-Kandidaten, Zaehler-/Pruefsummenwarnungen, Wiederholungswechsel, Bestaetigungsschutz, DEMO-Sperre
- Lokaler HTTP-Server: Demo-Status, statische UI, Signalkacheln, Editor, Messungsstart/-stopp, Benutzer-Events, CSV/JSON-Export, Demo-Umschaltung, simulierter USB-Verbindungsabbruch, DEMO-Ablehnung im Serialmodus
- Neuer Live-Monitor: `/api/monitor`, Ratenberechnung, ID-/Typ-Filter, inkrementelle Abfrage

## 4. Sicherheitscheck

Befehle:

```powershell
.venv\Scripts\python.exe tools\check_safety.py
.venv\Scripts\python.exe tools\check_local_safety.py
.venv\Scripts\python.exe tools\check_hardware_pins.py
.venv\Scripts\python.exe tools\check_board_config.py
```

Ergebnis: **bestanden**

- 29 C++-Quelldateien und 5 Python-Werkzeuge geprueft
- kein `twai_transmit`
- kein `TWAI_MODE_NORMAL`, TWAI ausschliesslich `TWAI_MODE_LISTEN_ONLY`
- keine CAN-Sendefunktion, keine OBD-/UDS-Anfragen
- kein `esp_deep_sleep_start`
- keine `digitalWrite(...)`-Pfade fuer GPIO1/GPIO2
- GPIO1/GPIO2 werden als `INPUT` (hochohmig) initialisiert, nicht als `OUTPUT`
- zentrale Pins: CAN TX=GPIO15, RX=GPIO16, RS485 TX=GPIO17, RX=GPIO18
- 16 MB Flash, `qio_opi`, USB-CDC, zwei 4-MB-App-Partitionen

## 5. Reale Hardware und Flashvorgang

Befehle:

```powershell
.venv\Scripts\pio.exe device list
.venv\Scripts\pio.exe pkg exec -- esptool --port COM8 flash-id
.venv\Scripts\pio.exe run -e esp32s3 -t upload
```

Ergebnis: **bestanden**

- Eindeutig erkanntes ESP-Geraet: **COM8**, USB `VID:PID=303A:1001`, Seriennummer `28:84:85:B4:15:84`
- Chip: **ESP32-S3 (QFN56), revision v0.2**, 240 MHz, Wi-Fi/BLE, **8 MB eingebettetes PSRAM**, **16 MB Flash**
- Flashvorgang: Bootloader, Partitionstabelle, `boot_app0.bin` und Firmware geschrieben; alle Hash-Pruefungen bestanden.
- Nach Reset erneut **COM8** erkannt (keine Aenderung der Portnummer).
- Boot-Log ueber USB-CDC gelesen:
  - `[USB] NDJSON-Logger aktiv`
  - `[BOOT] Volvo CAN Control V0.1 - PASSIVE ANALYSE`
  - `[BOOT] TWAI ausschliesslich LISTEN_ONLY, kein Senden.`
  - `[BOOT] GPIO1/GPIO2 hochohmig (INPUT), nicht angesteuert.`
  - `[OUT] ... Ausgaenge in V0.1 gesperrt.`
  - `[PWR] ... kein automatischer Deep Sleep.`
  - `[WLAN] AP 'Volvo-CAN-Control' gestartet, IP 192.168.4.1`
  - `[CAN] Aufzeichnungspuffer: 16384 Frames (PSRAM)`
  - `[CAN] TWAI LISTEN_ONLY gestartet, 500 kbit/s.`
  - `[WEB] HTTP auf http://192.168.4.1/`
  - `[STREAM] NDJSON auf TCP-Port 81`
  - `[SYS] Heap frei: 81296 Bytes, PSRAM frei: 7827356 Bytes, PSRAM gesamt: 8388608 Bytes`
- Der PSRAM-Puffer wurde erfolgreich alloziert. `psramFound()` der Arduino-Core-API meldet auf diesem Build `nein`, obwohl `heap_caps` 8 MB PSRAM und 7,8 MB frei meldet; `ESP.getFreePsram()` liefert deshalb 0. Die PSRAM-Nutzung selbst funktioniert (16.384-Frame-Puffer im PSRAM).

## 6. USB-Kommunikation und lokaler Server am realen ESP

Test: lokaler Diagnoseserver gegen COM8 ohne CAN-Bus.

Ergebnis: **bestanden**

- Server bindet auf `127.0.0.1:8765` (Testweise auch 8766/8767).
- `/api/health` meldet `volvo-can-diagnostics`.
- Status: `source=serial`, `connected=true`, `serial_port=COM8`.
- Keine CAN-Frames, weil kein CAN-Bus angeschlossen ist. Die Oberflaeche zeigt den vorgesehenen Hinweis auf Gateway/Anschlussstelle/Bitrate/CAN H/L/Terminierung.
- Keine Parse-Fehler; Diagnosezeilen werden getrennt von CAN-Nutzdaten verarbeitet.
- USB-CDC-Enumeration und COM-Port-Betrieb unter Windows sind damit real bestaetigt.

## 7. Demomodus Ende-zu-Ende

Test mit `local_can_diagnostics.py --demo` (synthetische Quelle, keine Hardware):

Ergebnis: **bestanden**

- Nach ca. 4 s: 79 Frames, 18,0 Nachrichten/s, 4 eindeutige IDs.
- Alle Frames sind als `DEMO` markiert; kein Frame ohne Demo-Kennzeichnung.
- Filter `0x1A0` + Standard: 22 Frames.
- 14 Signalkacheln; 13 davon `UNBEKANNT` (inkl. neuer Kachel **Tueren offen**), `CAN-Bus aktiv` = `AKTIV` (gruen).
- Aufzeichnung gestartet/gestoppt; CSV mit korrektem Header und 141 Zeilen erzeugt.
- Messassistent mit definierter Demo-Aktion: 2 Kandidaten gefunden, u. a. `0x1A0` Byte 0 Bit 0 (A=0, B=1), Score 38,5, `DEMO=true`.
- Kandidat an `reverse_gear` gebunden; Status bleibt **`candidate`**, nicht bestaetigt.
- Bestaetigungsschutz und DEMO-Sperre sind durch die Python-Tests abgedeckt.

## 8. Web-Oberflaechen

Befehle:

```powershell
.venv\Scripts\python.exe tools\check_web.py
.venv\Scripts\python.exe tools\check_local_web.py
node --check local_web\app.js
```

Ergebnis: **bestanden**

- Firmware-UI: 56 HTML-IDs, 25 in JavaScript verwendete IDs, 6 API-Pfade, keine CDN-Abhaengigkeit.
- Lokale UI: 84 HTML-IDs, 71 in JavaScript verwendete IDs, 15 API-Pfade, keine externen Ressourcen.
- JavaScript-Syntax mit Node 24.17.0 geprueft.
- Der neue Reiter **Live-CAN-Monitor** ist in HTML/JS vorhanden und liefert ueber `/api/monitor` CAN-ID, Datenbytes, DLC, STD/EXT, Nachrichten/s, Filter, Pause, Aufzeichnung und CSV-/JSONL-Export.
- Headless-Browser-Test mit Microsoft Edge gegen die Demo-Quelle: DOM nach 6 s enthielt den Monitor-Reiter, die Statistik **Nachrichten/s** und **102 gerenderte DEMO-Zeilen**; auch die Signalkacheln wurden gerendert. Damit ist die JavaScript-Ausfuehrung im Browser praktisch bestaetigt.
- Ein manueller visueller Klicktest durch den Benutzer steht noch aus.

## 9. Desktop-Starter

Ergebnis: **bestanden**

- Verknuepfung: `%USERPROFILE%\Desktop\Volvo CAN Control.lnk`
- Ziel: `%USERPROFILE%\Documents\Volvo-CAN-Control\start_volvo_can_control.bat`
- Der Starter erkennt COM8 automatisch, startet den lokalen Server auf `127.0.0.1:8765`, prueft die USB-Verbindung und oeffnet die Oberflaeche im Standardbrowser.
- Test ueber die Verknuepfung: Server erreichbar, `source=serial`, `connected=true`, `serial_port=COM8`, UI HTTP 200, `app.js` HTTP 200 mit Monitor-Code.
- Ohne ESP startet der Server trotzdem und die Oberflaeche zeigt einen verstaendlichen Verbindungsfehler.

## 10. Nicht durchgefuehrte Tests

Ausdruecklich **nicht** getestet:

- CAN-Empfang am realen Fahrzeug (kein OBD2-Anschluss hergestellt).
- Reale CAN-Bitrate 500/250/125 kbit/s und Bus-Off-Verhalten am Volvo.
- Elektrische Messung der CAN-Terminierung und der Board-Pins am realen Exemplar (nur Dokumentenabgleich; Durchgangsmessung vor Fahrzeuganschluss noetig).
- Aktive Verbindung zum WLAN-Access-Point des ESP32 und Bedienung der ESP-Weboberflaeche vom Laptop (Laptop-WLAN blieb unveraendert).
- Ausgabe echter CAN-Frames ueber USB-CDC (ohne CAN-Bus bzw. ohne aktivierten Firmware-Demo-Modus nicht erzeugbar).
- Volvo-Gateway-/OBD-Firewall-Verhalten.
- Praktische Identifikation und Bestaetigung von V90-2021-Signalen.
- Automatisierter visueller Browser-Klicktest der lokalen Oberflaeche.
- USB-Logger-Integrationstest unter Windows mit PTY (Windows-PTY nicht verfuegbar; Parser/CSV und Server-Serialpfad sind anderweitig getestet).

## 11. Reproduktion

```powershell
cd %USERPROFILE%\Documents\Volvo-CAN-Control
.venv\Scripts\python.exe tools\check_board_config.py
.venv\Scripts\python.exe tools\check_hardware_pins.py
.venv\Scripts\python.exe tools\check_safety.py
.venv\Scripts\python.exe tools\check_local_safety.py
.venv\Scripts\python.exe tools\check_web.py
.venv\Scripts\python.exe tools\check_local_web.py
node --check local_web\app.js
.venv\Scripts\python.exe -m unittest discover -s test -v
.venv\Scripts\pio.exe run -e esp32s3
.venv\Scripts\pio.exe test -e native
.venv\Scripts\pio.exe run -e esp32s3 -t upload
```


## Server-Split und Re-Tests am 2026-11-05

Das Projekt wurde auf dem MGMT-Core in `OBD-Low-Bus/` und `OBD-CEM-Bus/`
getrennt. Der Low-Bus-Stand wurde aus der neueren Windows-Kopie uebernommen;
alle Messungen und Decoder-Kandidaten blieben erhalten.

### Firmware-Build OBD-Low-Bus

- PlatformIO Core 6.2.0, `espressif32@8.0.0`, Arduino Core 3.3.12
- Ergebnis: **SUCCESS**
- RAM: 58,4 % (191.524 / 327.680 Bytes)
- Flash: 30,2 % (1.266.483 / 4.194.304 Bytes)

### Native C++-Tests

- `pio test -e native` mit `test_dir = ../tests`
- Ergebnis: **9 von 9 bestanden**

### Python-Tests

- `python3 -m unittest discover -s tests -v`
- Ergebnis: **30 von 30 bestanden**
- Enthalten: USB-Logger-PTY-Simulation, lokaler HTTP-Server, Demo, Export,
  Signal-Engine, A/B-Assistent, Sicherheits-/Validierungslogik

### Statische Checks

- `check_board_config.py`: OK (16 MB Flash, OPI-PSRAM, USB-CDC)
- `check_hardware_pins.py`: OK (CAN TX=GPIO15, RX=GPIO16; RS485 17/18)
- `check_safety.py`: OK (nur LISTEN_ONLY, kein Senden, GPIO1/2 hochohmig)
- `check_local_safety.py`: OK
- `check_web.py`: OK (56 HTML-IDs, 25 JS-IDs, 6 API-Pfade)
- `check_local_web.py`: OK (85 HTML-IDs, 71 JS-IDs, 15 API-Pfade)

### Demo-/Profil-Smoke-Test

- Demo-Server mit Profil `OBD-Low-Bus`: 20 Signale, Demo-Frames, UI HTTP 200
- CSV-Export: Header korrekt; JSON-Export: Liste korrekt
- Profil-Sperre: Start von `OBD-CEM-Bus` auf demselben Port wurde abgewiesen
- Es wurde kein ESP geflasht und kein Fahrzeug angeschlossen.

### Identifizierte OBD-Low-Bus-Kandidaten

| Signal | CAN-ID | Byte | Maske | Aktivwert | Status |
|---|---|---|---|---|---|
| Fahrstufe P | 0x1FFF00A0 | 6 | 0x03 | 0x00 | Kandidat |
| Fahrstufe R | 0x1FFF00A0 | 6 | 0x03 | 0x01 | Kandidat |
| Fahrstufe N | 0x1FFF00A0 | 6 | 0x03 | 0x02 | Kandidat |
| Fahrstufe D | 0x1FFF00A0 | 6 | 0x03 | 0x03 | Kandidat |
| Fussbremse | 0x1FFF0200 | 4 | 0x02 | 0x02 | Kandidat |
| Rueckfahrkamera | 0x1FFF0144 | 2 | 0x08 | 0x00 | Kandidat |

Nicht auf dem OBD-Diagnosebus sichtbar: Abblendlicht, Fernlicht,
Standlicht, Parkbremse, manuelle 360-Grad-Kamera, Tueren/Verriegelung,
Fenster, Spiegel, Sitz, Lenkradtasten, Kofferraum.

### Offene Punkte

- Formale Drei-Lauf-Bestaetigung der Kandidaten steht noch aus.
- Echter Fahrzeug-CAN/Vehicle-Test auf dem Server nicht durchgefuehrt.
- Body-/Licht-/EPB-Signale benoetigen einen Body-CAN-Zugang.
