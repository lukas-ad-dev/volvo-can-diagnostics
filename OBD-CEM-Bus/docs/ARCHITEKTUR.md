# Architektur

## Ueberblick

```
CAN-Bus (nur RX) ──> TWAI LISTEN_ONLY ──> CanManager-Task
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       │                     │                     │
                 Live-Ringpuffer        ID-Statistik         Phasen A/B
                 (intern, 1024)         (max. 256 IDs)       (je 256 IDs)
                       │                     │                     │
                       ├──────────────> WebServer (HTTP 80) <──────┘
                       │                     │
                       ├──────────────> UsbLogger (USB-CDC, NDJSON, Queue)
                       └──────────────> StreamServer (TCP 81, NDJSON)

DemoGenerator ──> gleicher CanManager-Pfad (jeder Frame demo=true)
```

Der Demo-Generator und der TWAI-Empfang sind zwei Quellen derselben Pipeline. Es gibt keinen Pfad, der Demo-Frames als echte Frames ausgibt. Beim Quellwechsel werden Live-Ring, Statistik, Phasen und Aufzeichnung geleert.

## Firmware-Komponenten

| Datei | Aufgabe |
| --- | --- |
| `main.cpp` | Boot, Access Point, Initialisierung, Web-Loop |
| `settings.*` | NVS: feste Bitrate 500 kbit/s und Demo-Modus |
| `can_manager.*` | TWAI Listen-Only, Boot = STOP, START gesperrt, Dummy-TX, Demo-Quelle, Ringpuffer, Statistik, Phasen, Aufzeichnung |
| `capture_buffer.*` | Aufzeichnungspuffer im PSRAM mit internem Fallback |
| `web_server.*` | HTTP-API und Auslieferung der Weboberflaeche |
| `usb_logger.*` | USB-CDC-NDJSON-Logger, entkoppelte Queue, Verwurf-/Fehlerzaehler |
| `stream_server.*` | NDJSON-Stream auf TCP-Port 81 |
| `output_control.*` | GPIO1/GPIO2, hochohmig (INPUT) und hart gesperrt |
| `power_manager.*` | vorbereitete Schlafarchitektur ohne Deep Sleep |
| `lib/volvo_core` | plattformunabhaengige Logik: Frames, Ring, Statistik, Vergleich, Demo, CSV |

## Tasks und Nebenlaeufigkeit

- **Arduino-Loop:** WebServer (`handleClient`), keine blockierenden CAN-Zugriffe.
- **CAN-Task (Core 1):** TWAI-Empfang oder Demo-Erzeugung, maximal 16 Frames pro Durchlauf, kurze Delays.
- **USB-Logger-Task (Core 0):** empfaengt Frames aus einer eigenen Queue und schreibt NDJSON ueber USB-CDC. Nicht blockierend; volle Queue/USB-Buffer werden gezaehlt. Diagnosezeilen beginnen mit `# `.
- **Stream-Task (Core 0):** maximal zwei TCP-Clients, sendet neue Frames als NDJSON.
- **Mutex:** Ein FreeRTOS-Mutex schuetzt Statistik, Live-Ring, Aufzeichnung und Phasen. Der CAN-Task haelt ihn nur kurz pro Frame; HTTP-Exporte arbeiten mit einer Kopie bzw. einem PSRAM-Snapshot, damit der Empfang nicht lange blockiert.

## Speicher

- **Live-Ring:** 1024 Frames im internen RAM (ca. 24 KB).
- **Aufzeichnung:** 16384 Frames im PSRAM (ca. 393 KB); falls PSRAM fehlt, 2048 Frames im internen RAM.
- **ID-Statistik:** maximal 256 IDs pro Tabelle; je Phase eine Tabelle, dazu die Live-Tabelle.
- **Vergleich:** maximal 256 Eintraege; bei mehr IDs wird `truncated=true` gemeldet.
- **TWAI-RX-Queue:** 512 Frames, 64 Frames pro Task-Durchlauf, damit hohe Buslast nicht unnoetig verloren geht.
- **USB-Queue:** 512 Frames (ca. 12 KB), entkoppelt USB-Schreiben vom CAN-Empfang.
- **Web-UI:** als `PROGMEM`-String eingebettet, kein LittleFS-Upload noetig.
- **Demo- und Stream-Daten:** keine dynamischen Dauerspeicher; NDJSON wird direkt geschrieben.

## USB-CDC-Format

Der USB-Logger sendet eine NDJSON-Zeile pro CAN-Frame:

```json
{"type":"can","seq":42,"timestamp_us":1234567,"id":416,"id_hex":"0x1A0","extended":false,"dlc":8,"data":"0102030405060708","demo":false}
```

Diagnosemeldungen werden nicht als CAN-Frame ausgegeben, sondern mit dem Praefix `# ` gesendet, z. B.:

```
# [USB-STATS] tx=1000 dropped=0 txerr=0 diagdrop=0 queue=0/512
```

Der Windows-Logger trennt beides: CAN-Zeilen gehen in CSV-Dateien, `#`-Zeilen in die Event-Logdatei.

## HTTP-API

| Methode | Pfad | Zweck |
| --- | --- | --- |
| GET | `/` | Weboberflaeche |
| GET | `/style.css`, `/app.js` | UI-Ressourcen |
| GET | `/api/status` | Dashboard, Phasen, Aufzeichnung, Einstellungen, USB-Zaehler |
| GET | `/api/messages?since=&limit=` | neue Live-Frames, maximal 200 pro Abruf |
| GET | `/api/stats` | aggregierte ID-Statistik |
| POST | `/api/settings` | `{bitrate, demo}`; startet Quelle neu |
| POST | `/api/phase` | `{phase:"A"/"B", action:"start"/"stop"}` oder `{action:"reset"}` |
| GET | `/api/compare` | Vergleichsergebnis als JSON |
| GET | `/api/compare/export?format=csv\|json` | Vergleich als Download |
| POST | `/api/record` | `{action:"start"/"stop"}` |
| GET | `/api/export/csv` | Aufzeichnung als CSV (nur gestoppt) |
| GET | `/api/export/json` | Aufzeichnung als JSON (nur gestoppt) |
| POST | `/api/clear` | Live-Ringpuffer leeren |

Der TCP-Port 81 ist kein HTTP-Endpunkt, sondern ein reiner NDJSON-Stream fuer den Python-Collector.

## Sicherheitsdesign

- TWAI wird ausschliesslich mit `TWAI_MODE_LISTEN_ONLY` installiert.
- CAN TX/RX kommen zentral aus `lib/volvo_core/include/volvo_core/hardware_pins.h`. Bestaetigte Waveshare-Belegung (04.11.2026): **CAN TX=GPIO15, RX=GPIO16; RS485 TX=GPIO17, RX=GPIO18**. `static_asserts` und `tools/check_hardware_pins.py` schuetzen diese Zuordnung. Vor dem Anschluss am Fahrzeug ist trotzdem eine optische/Durchgangspruefung am realen Board sinnvoll.
- Es gibt keine Funktion, die `twai_transmit` aufruft. `tools/check_safety.py` prueft das statisch.
- Es gibt keine Diagnose-, Replay- oder Gateway-Funktion.
- GPIO1/GPIO2 werden nur als hochohmige Eingaenge (INPUT) initialisiert und nie aktiv getrieben. Die Klasse `OutputGuard` liefert immer `false`; weder HIGH noch LOW ist im Quellcode erreichbar. Das ist wichtig, weil ein LOW-Pegel ein LOW-aktives Relais einschalten koennte.
- `PowerManager` ruft kein `esp_deep_sleep_start` auf und interpretiert CAN-Stille nicht als Fahrzeug-Ruhe.
- Aufzeichnung und Export sind auf einen Ringpuffer begrenzt; verworfene Frames werden gezaehlt und angezeigt.

## Bekannte Grenzen

- Keine Echtzeitgarantie: WiFi/WebServer und Logging koennen Frames verzoegern; der Live-Ring kann ueberlaufen.
- Der Python-Stream ist verlustbehaftet, wenn der Laptop oder WLAN kurz aussetzt.
- Die Phasenanalyse ist eine Heuristik; Frequenz- und Bitvergleiche ersetzen keine Signaldefinition.
- Kein RTC-Wanduhrzeitstempel; Zeit ist monoton seit Boot.
- Kein OTA-Update; Flashen nur per USB.
- Keine echte Hardware-Validierung in diesem Stand.

## Lokale Windows-Signalerkennung

Die lokale Diagnose ist eine separate Python-Anwendung und greift nicht in die Firmware ein:

```
ESP32 USB-CDC / TCP-NDJSON
        │
        ▼
usb_can_logger.py  (Parse, CSV, Event-Log)
        │
        ▼
local_can_diagnostics.py  (ThreadingHTTPServer 127.0.0.1:8765)
        │
        ├── signal_engine.py   (LEDs, Editor, A/B-Pruefablauf, Bestaetigung)
        ├── config/signals.json
        ├── config/confirmed_signals.json
        ├── config/reference_ids.json
        ├── config/generated/esp32_signals.json
        └── messungen/ (Session- und Mess-CSV, Roh-JSONL, Events-JSONL, Meta)
```

- **Nur lokal:** Der HTTP-Server bindet standardmaessig an `127.0.0.1`; das normale WLAN des Laptops bleibt unveraendert.
- **Nur lesend:** Die Python-Anwendung oeffnet den seriellen Port ausschliesslich lesend; es gibt keinen CAN-Sendezpfad.
- **Demo exklusiv:** `--demo` verwendet eine synthetische Quelle und einen getrennten Ordner `messungen/demo`. DEMO-Frames werden im Serialmodus ignoriert, damit echte und synthetische Daten nicht vermischt werden.
- **Rohdaten:** Jede Session schreibt Session-CSV, Roh-JSONL (Frames + Meta), Events-JSONL, Event-Log und Meta-JSON. GUI-Filter beeinflussen die Rohaufzeichnung nicht.
- **Status:** `UNBEKANNT`, `KANDIDAT`, `IN PRUEFUNG`, `BESTAETIGT`, `VERWORFEN`; Bestaetigung nur mit mindestens drei unabhaengigen Pruefablaeufen, mindestens zwei Aktionsbezeichnungen, Checkliste und Notiz; DEMO-Evidenz ist gesperrt.
- **Fehlende Frames:** Die Oberflaeche weist auf Gateway, OBD-Anschlussstelle, Bitrate und CAN H/L hin und behauptet keinen automatischen Firmwarefehler.
