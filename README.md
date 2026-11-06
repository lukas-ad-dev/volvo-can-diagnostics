# Volvo CAN

Hier dokumentiere ich meine passive Analyse der CAN-Busse in einem Volvo V90
T8 (SPA, Modelljahr 2021). Als Hardware nutze ich ein Waveshare
ESP32-S3-RS485-CAN. Der Schwerpunkt liegt auf dem internen CEM-Bus und den
Werkzeugen, mit denen ich die Nachrichten aufzeichne und auswerte.

## Fahrzeug und Busse

| Bereich | Beschreibung |
|---|---|
| Fahrzeug | Volvo V90 T8, SPA, Modelljahr 2021 |
| OBD-Diagnosebus | OBD2 Pin 6/14, älterer Analysepfad |
| CEM-CAN | interner CAN-Bus hinter dem Fahrerfach |
| Bitrate CEM | 500 kbit/s, mit echten Frames geprüft |
| Betriebsart | nur passiv, kein Senden |

Ich lese ausschließlich mit. Das Projekt sendet keine CAN-Nachrichten, stellt
keine Diagnoseanfragen und verändert keine Steuergeräte.

## Was ich bisher gefunden habe

Die folgende Tabelle zeigt den aktuellen Stand aus mehreren Aufzeichnungen.
Einige Zustände sind im Test mehrfach aufgetreten, andere sind noch offen.

| Funktion | CAN-ID | Feld | Zustand | Stand |
|---|---|---|---|---|
| Licht aus / Standlicht | `0x030`/`0x035` | Byte 2-3 | `7C61` | beobachtet |
| Wegbeleuchtung / Coming Home | `0x030`/`0x035` | Byte 2-3 | `7C60` | Kandidat |
| Abblendlicht | `0x030`/`0x035` | Byte 2-3 | `86 03` | im Test bestätigt |
| Fernlicht manuell | `0x030`/`0x035` | Byte 2-3 | `92 2B` | im Test bestätigt |
| Fernlicht Automatik/Nacht | `0x030`/`0x035` | Byte 2-3 | `92 6B` | im Test bestätigt |
| Fernlicht weitere Basis | `0x030`/`0x035` | Byte 2-3 | `92 4B` | beobachtet |
| Fernlicht generisch | `0x030`/`0x035` | Byte 2-3 | Maske `0x9008` | Kandidat |
| Lichthupe | `0x030`/`0x035` | Byte 2-3 | `7C69` | bei Abblendlicht aus bestätigt |
| Blinker links | `0x040` | Byte 5, Bit 4 | 0/1 | beobachtet |
| Blinker rechts | `0x040` | Byte 5, Bit 5 | 0/1 | beobachtet |
| Warnblinker | `0x040` | Byte 5, Bits 4+5 | beide 1 | beobachtet |
| Blinkstatus normal | `0x050` | Byte 4-7 | `01 90 01 90` | links/rechts |
| Warnblinkerstatus | `0x050` | Byte 4-7 | `01 F4 01 2C` | Warnblinker |

`0x030` und `0x035` sind Zwillingsnachrichten. Die Bytes 1 bis 7 sind gleich,
Byte 0 unterscheidet sich immer um XOR `0x65`. Byte 0 ist ein Zähler- und
Integritätsfeld, kein Schaltsignal. In `0x040` Byte 5 wechseln zusätzlich
einige Zählerbits sehr schnell. Für den Blinker zählen nur Bit 4 und Bit 5.

## Was noch offen ist

Den Einschaltbefehl für die Wegbeleuchtung habe ich noch nicht gefunden.
Während der Wegbeleuchtung bleibt `0x030`/`0x035` auf `7C60`. Beim Aufwachen
des Busses erscheinen `0x531` (`31 40 ...`) und `0x532` (`32 40 ...`). Das
sieht nach Network-Management aus, nicht nach einem Lichtbefehl.

Bremspedal und Fahrstufe N/R konnte ich auf dem CEM-11-Bit-Bus nicht als
stabile Zustände sehen. Die bekannten Referenzen liegen im OBD-Low-Bus-Bereich
(`0x1FFF...`) und müssen dort geprüft werden.

Die Hardware ist noch nicht vollständig durchgemessen. Offen sind vor allem
der 120-Ohm-Jumper, die Verkabelung und der TXD-Pfad.

## Werkzeuge

Die lokale Oberfläche läuft auf Windows und bietet:

- Live-Monitor mit Filter für CAN-IDs und Ausblenden von Dauersignalen
- Prüfablauf mit einem Aktionszyklus und Live-Anzeige EIN/AUS
- Bit-Test für bis zu 60 Bits, die sich während des Tests ändern
- Signalanalyse mit A/B-Vergleich, Bitmatrix, Zeitdiagramm und CSV/JSON-Export
- Messungen mit eigenem Namen, Start/Stop und getrennten CSV-Dateien
- Kompakte Signal-Karten, Details per Klick und ein Archiv für alte Kandidaten

## Aufbau

| Ordner | Inhalt |
|---|---|
| `OBD-CEM-Bus/` | Firmware, lokale Oberfläche, Signalanalyse, Bit-Test, CEM-Doku |
| `OBD-Low-Bus/` | OBD-Analyse, Signalkandidaten, Logger und Tools |

## Bauen und testen

```bash
cd OBD-CEM-Bus/firmware
pio run -e esp32s3
pio test -e native

cd ../..
python -m unittest discover -s OBD-CEM-Bus/tests -p "test_*.py"
python OBD-CEM-Bus/tools/check_local_safety.py
python OBD-CEM-Bus/tools/check_local_web.py
```

## Start unter Windows

Die Firmware läuft über USB-CDC. Der lokale Server ist unter
`http://127.0.0.1:8765/` erreichbar. Startskripte und weitere Hinweise liegen
im jeweiligen Projektordner.

## Dokumentation

- [`PROJEKTVERLAUF.md`](PROJEKTVERLAUF.md): Fahrzeug, Ziel und bisheriger Verlauf
- [`ERGEBNISSE.md`](ERGEBNISSE.md): Messwerte, CAN-IDs und Signalkandidaten
- `OBD-CEM-Bus/docs/`: Hardware, Sicherheit, Architektur und CEM-Test
- `OBD-Low-Bus/docs/`: OBD-Messungen und Signalerkennung
- Im Wiki: `Projekt:Volvo/CAN`

## Lizenz

MIT-Lizenz, siehe [`LICENSE`](LICENSE). Copyright (c) 2026 lukas-ad.

## Hinweis

Das Projekt gehört nicht zu Volvo Cars. Die CAN-IDs und Zustände sind meine
eigenen Analyseergebnisse und keine offiziellen Herstellerdaten. Arbeiten am
Fahrzeug nur bei sicherem Stand und mit passender Hardware.
