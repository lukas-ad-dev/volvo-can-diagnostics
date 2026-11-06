# Projektverlauf – Volvo CAN Diagnostics

## Fahrzeug

- **Modell:** Volvo V90
- **Variante:** T8
- **Plattform:** SPA
- **Modelljahr:** 2021

## Ziel

Passive Analyse von zwei CAN-Bussen im eigenen Fahrzeug:

1. **OBD-Diagnosebus** (OBD2 Pin 6/14) – älterer Analysepfad.
2. **Interner CEM-CAN** – neuerer, passiver Abgriff hinter dem Fahrerfach.

Gesuchte Signale (zunächst alle **UNBEKANNT**):

- Rückwärtsgang, Fahrgeschwindigkeit
- Abblendlicht, Fernlicht, Standlicht
- Parkkamera/Rangiermodus
- Ver-/Entriegelung, Fahrertür
- Zündung, Komfort/Radio, Fahrzeug wach/Ruhezustand

**Ausdrücklich nicht Ziel:** CAN senden, Diagnoseanfragen, Gateway-Manipulation,
Steuergeräte codieren oder Fahrzeugfunktionen steuern. Das Projekt ist
**read-only**.

## Hardware

- Waveshare **ESP32-S3-RS485-CAN**
- Isolierter CAN-Transceiver TJA1051, Digitalisolator π163E31
- CAN TX = GPIO15, CAN RX = GPIO16
- Sicherheitsmaßnahme: echter TXD GPIO15 bleibt `INPUT_PULLUP`;
  TWAI-TX liegt auf Dummy-GPIO48
- 120-Ω-Terminierung am Board: Standard NC; am realen Board prüfen
- USB-CDC zur Diagnose, optional WLAN-AP der Firmware

## Verlauf

### 2026-11-04 – OBD-Low-Bus

- Erste passive Hardwaretests am OBD2-Port.
- USB-Logger, lokale Weboberfläche, CSV-Aufzeichnung.
- Erste Kandidaten:
  - Fahrstufe P/R/N/D: `0x1FFF00A0`, Byte 6, Bits 0–1
  - Fußbremse: `0x1FFF0200`, Byte 4, Bit 1
  - Rückfahrkamera: `0x1FFF0144`, Byte 2, Bit 3 (aktiv bei 0)
- Abblendlicht, Fernlicht, Standlicht, Parkbremse und manuelle Kamera waren
  auf dem beobachteten OBD-Diagnosebus **nicht stabil** sichtbar.
- Diese IDs sind Referenz/Kandidaten, **keine bestätigten CEM-Decoder**.

### 2026-11-05 – CEM-CAN und Sicherheitsvorfall

- Aufbau des CEM-Projekts und Analyse der internen Busdaten.
- Ein früherer automatischer Bitratenscan mit wiederholten
  TWAI-Initialisierungen führte zu Fahrzeugstörungen (Blinkleuchten/
  Beleuchtung). Nach Trennen der USB-Versorgung verschwanden sie.
- Konsequenz: keine Scans mehr, fester 500-kbit/s-Testbetrieb, nur
  LISTEN_ONLY, expliziter START, kein Auto-Neuversuch, Dummy-TX-Schutz.
- Auswertung der 500-kbit/s-Logs: **159.617 Frames**, 24 Standard-IDs,
  keine Demo-/Parse-Fehler; 8.735 Frames/10 s plausibel bestätigt.
- Firmware auf 500 kbit/s festgelegt; Errata-Workaround
  `CONFIG_TWAI_ERRATA_FIX_LISTEN_ONLY_DOM=1` aktiv.

### 2026-11-06 – Live-Test und Assistent

- Autorisierter read-only Live-Test: **289.647 Frames**, **24 IDs**,
  **0 CAN-Fehler**, 33 USB-Queue-Drops, TWAI **RUNNING**.
- Danach sauberer STOP; keine CAN-Sendeaktion.
- Assistent auf **zwei Aktionszyklen** erweitert:
  AUS → EIN → AUS → EIN → Auswertung.
- Kandidaten zeigen live `EIN/AUS`; Zielsignal-Auswahl pro Kandidat wird
  beim Binden übernommen.
- Letzter Test „standlicht“ ergab 0 Kandidaten, weil in beiden EIN-Zyklen
  kein Bit stabil wechselte. Das war kein UI-Fehler, sondern die Aktion
  erzeugte im CEM-Datenstrom keinen reproduzierbaren Zustandswechsel.
- Repository mit Code, Doku, Hardware- und CAN-Bus-Infos erstellt.

## Bisherige Ergebnisse

| Bereich | Ergebnis |
|---|---|
| CEM-Bitrate | 500 kbit/s durch echte Frames plausibel bestätigt |
| CEM-Frames | 159.617 (Loganalyse), 289.647 (Live-Lauf) |
| CEM-IDs | 24 Standard-IDs, keine Extended-IDs |
| CEM-Fehler | 0 CAN-/Bus-/TX-/RX-Fehler im Live-Lauf |
| OBD-Low-Signale | Fahrstufe, Fußbremse, Rückfahrkamera als Kandidaten |
| CEM-Decoder | noch keine bestätigten CEM-Signale |
| Assistent | zwei Zyklen, Live-Bit-Anzeige, Bind-Auswahl |
| Hardware-Passivität | noch nicht messtechnisch vollständig nachgewiesen |

## Offene Fragen

Diese Angaben fehlen noch und können vom Fahrzeughalter ergänzt werden:

1. Genaue Ausstattung/Antriebsbezeichnung (z. B. T8 Recharge) und ob weitere
   Steuergeräte bekannt sind.
2. Genaue Einbauposition und Kabelfarben des CEM-Abgriffs.
3. Board-Revision und tatsächliche Jumperstellung der 120-Ω-Terminierung.
4. Oszilloskopmessung: GPIO15/TXD, U9-Ausgang und CAN-H/L bei Boot/START/STOP.
5. Ob 500 kbit/s exakt dem CEM-Bus entsprechen (zweite Gegenmessung).
6. Welche Signale Priorität haben (Rückwärtsgang, Licht, Ambient, Kamera).
