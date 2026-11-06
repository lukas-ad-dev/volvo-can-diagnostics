# Volvo CAN Diagnostics – CEM & OBD Low Bus

Passive CAN-Analyse für einen **Volvo V90 T8 (SPA-Plattform, Modelljahr 2021)**
mit dem Waveshare **ESP32-S3-RS485-CAN**. Das Projekt dokumentiert zwei
CAN-Busse und die Werkzeuge, mit denen Nachrichten ausschließlich gelesen und
ausgewertet werden.

## Fahrzeug und Busse

| Bereich | Beschreibung |
|---|---|
| Fahrzeug | Volvo V90 T8, SPA, Modelljahr 2021 |
| OBD-Diagnosebus | OBD2 Pin 6/14, älterer Analysepfad |
| CEM-CAN | interner CAN-Bus hinter dem Fahrerfach |
| Bitrate CEM | 500 kbit/s (durch Live-Messung bestätigt) |
| Betriebsart | ausschließlich LISTEN_ONLY, kein Senden |

## Ziel

Die Signale des Fahrzeugs werden passiv identifiziert und dokumentiert:

- Rückwärtsgang und Fahrgeschwindigkeit
- Abblendlicht, Fernlicht, Standlicht, Wegbeleuchtung
- Blinker links/rechts und Warnblinker
- Parkkamera und Rangiermodus
- Ver- und Entriegelung, Fahrertür
- Zündung, Komfort/Radio, Fahrzeug wach/Ruhezustand

Das Projekt sendet **keine CAN-Nachrichten**, stellt keine Diagnoseanfragen und
verändert keine Steuergeräte.

## Aktueller Stand – 2026-11-06

### CEM-CAN

- **500 kbit/s**, fester Testbetrieb, **LISTEN_ONLY**
- **24 Standard-11-Bit-IDs**, keine Extended-IDs auf diesem Abgriff
- Live-Aufzeichnungen mit mehreren Millionen Frames
- Im normalen Empfang **0 Busfehler**; Busfehler treten nur im Zusammenhang mit
  Bus-Schlaf-/Wake-Zyklen auf
- Echter TXD bleibt `INPUT_PULLUP`; TWAI-TX nutzt einen Dummy-Pin
- Kein Auto-Start, kein Bitratenscan, kein Auto-Neuversuch

### Erkannte Licht- und Blinkzustände

Die wichtigsten bisher reproduzierbaren Zustände:

| Funktion | CAN-ID | Feld | Zustand | Bewertung |
|---|---|---|---|---|
| Licht AUS/Standlicht | `0x030`/`0x035` | Byte 2–3 | `7C61` | beobachtet |
| Wegbeleuchtung/Coming Home | `0x030`/`0x035` | Byte 2–3 | `7C60` | Kandidat |
| Abblendlicht | `0x030`/`0x035` | Byte 2–3 | `86 03` | praktisch bestätigt |
| Fernlicht manuell | `0x030`/`0x035` | Byte 2–3 | `92 2B` | praktisch bestätigt |
| Fernlicht Automatik/Nacht | `0x030`/`0x035` | Byte 2–3 | `92 6B` | praktisch bestätigt |
| Fernlicht weitere Basis | `0x030`/`0x035` | Byte 2–3 | `92 4B` | beobachtet |
| Fernlicht generisch | `0x030`/`0x035` | Byte 2–3 | Maske `0x9008` | Kandidat |
| Lichthupe | `0x030`/`0x035` | Byte 2–3 | `7C69` | bei Abblendlicht AUS bestätigt |
| Blinker links Befehl | `0x040` | Byte 5, Bit 4 | 0/1 | beobachtet |
| Blinker rechts Befehl | `0x040` | Byte 5, Bit 5 | 0/1 | beobachtet |
| Warnblinker Befehl | `0x040` | Byte 5, Bits 4+5 | beide 1 | beobachtet |
| Blinkstatus normal | `0x050` | Byte 4–7 | `01 90 01 90` | links/rechts |
| Warnblinkerstatus | `0x050` | Byte 4–7 | `01 F4 01 2C` | Warnblinker |

`0x030` und `0x035` sind Zwillingsnachrichten: Bytes 1–7 sind identisch, Byte 0
unterscheidet sich konstant um XOR `0x65`. Byte 0 ist ein Zähler/Integritätsfeld
und kein Schaltsignal. `0x040` Byte 5 enthält außerdem stark flatternde
Zählerbits; nur die Bits 4 und 5 sind für die Blinker relevant.

### Offene Punkte

- Der **Trigger-Befehl für Wegbeleuchtung/Coming Home** wurde noch nicht
  gefunden. Beim Bus-Schlaf/Wake erscheinen `0x531`/`0x532` mit
  `31 40 …`/`32 40 …`; das sind wahrscheinlich Network-Management-/Wake-Frames,
  kein Lichtbefehl.
- **Bremspedal und Fahrstufe N/R** waren auf dem CEM-11-Bit-Bus nicht als
  stabile Zustände sichtbar. Die bekannten Referenzen liegen im
  OBD-Low-Bus-Bereich (`0x1FFF...`) und müssen dort geprüft werden.
- Die Hardware-Passivität (120-Ω-Jumper, Verkabelung, Isolator/TXD) ist noch
  nicht vollständig messtechnisch nachgewiesen.

## Projekte

| Ordner | Inhalt |
|---|---|
| `OBD-CEM-Bus/` | Firmware, Web-GUI, Signalanalyse, Bit-Test, CEM-Dokumentation |
| `OBD-Low-Bus/` | passive OBD-Analyse, Signalkandidaten, Logger und Tools |

## Werkzeuge

Die lokale Windows-Oberfläche bietet:

- Live-CAN-Monitor mit ID-Filter und Ausblenden von Dauersignalen
- Assistent mit einem Aktionszyklus und Live-EIN/AUS-Anzeige
- Bit-Test für bis zu 60 ändernde Bits
- Signalanalyse mit A/B-Vergleich, Bitmatrix, Zeitdiagramm und CSV/JSON-Export
- Messungsverwaltung: Start/Stop mit eigenem Namen, getrennte CSV-Dateien
- Kompakte Signal-Karten; Details erst auf Klick; Altbestände im Archiv

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

Die CEM-Firmware wird über USB-CDC angesprochen. Der lokale Diagnoseserver
läuft auf `http://127.0.0.1:8765/`. Startskripte und weitere Hinweise liegen
im jeweiligen Projektordner.

## Dokumentation

- [`PROJEKTVERLAUF.md`](PROJEKTVERLAUF.md) – Fahrzeug, Ziel, Zeitlinie und
  Entwicklung
- [`ERGEBNISSE.md`](ERGEBNISSE.md) – Messwerte, CAN-IDs und Signalkandidaten
- `OBD-CEM-Bus/docs/` – Hardware, Sicherheit, Architektur und CEM-Test
- `OBD-Low-Bus/docs/` – OBD-Messungen und Signalerkennung
- Öffentliche Projektseite: **Lukas AD Wiki → Projekt:Volvo/CAN**

## Lizenz

**MIT-Lizenz** – siehe [`LICENSE`](LICENSE). Copyright (c) 2026 **lukas-ad**.

## Hinweis

Dieses Projekt steht in keiner Verbindung zu Volvo Cars. CAN-IDs und
Signalangaben sind eigene Analyseergebnisse und keine offiziellen
Herstellerdaten. Arbeiten am Fahrzeug nur bei sicherem Stand und mit
passender Hardware; die Verantwortung für den Eingriff liegt beim Betreiber.
