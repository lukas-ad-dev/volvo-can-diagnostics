# Roadmap

## V0.1 - Passive Analyse (aktueller Stand)

- [x] PlatformIO-Projekt fuer Waveshare ESP32-S3-RS485-CAN
- [x] TWAI ausschliesslich `LISTEN_ONLY`, keine Sendeaufrufe
- [x] WLAN-Access-Point und deutsche responsive Weboberflaeche
- [x] Live-Monitor, Filter, Pause, Loeschen, Ausblenden, Sortieren
- [x] Zwei Messphasen mit Byte-/Bit-/Frequenzvergleich
- [x] Ringpuffer im PSRAM, CSV-/JSON-Export
- [x] Python-CSV-Collector fuer Windows (TCP) und USB-CDC-Logger
- [x] Benannte Messszenarien, Session-CSV, Event-Log und Messungsvergleich
- [x] Lokale Windows-Signalerkennung auf 127.0.0.1:8765 mit Signalkacheln, Editor und Assistent
- [x] Bestaetigungsschutz mit mindestens drei dokumentierten Assistenten-Laeufen
- [x] Quellen-/Plattformtrennung in CAN_REFERENZEN.md und reference_ids.json
- [x] Demo-Modus mit eindeutiger DEMO-Kennzeichnung
- [x] GPIO1/GPIO2 vorbereitet und hart gesperrt
- [x] Energiespararchitektur ohne automatischen Deep Sleep
- [x] Native Tests, Python-Tests, Sicherheitscheck, Firmware-Build

## V0.2 - Messqualitaet und Komfort

- [ ] RTC PCF85063 optional fuer Wanduhrzeit in CSV/JSON nutzen
- [ ] Aufzeichnung auf microSD oder externen Speicher (Hardwareerweiterung)
- [ ] Konfigurierbare CAN-Filter (nur bestimmte IDs aufzeichnen)
- [ ] Laengere Ringpuffer/Streaming-Optimierung
- [ ] Import der CSV/JSON-Dateien in eine Desktop-Auswertung
- [ ] Vergleich mehrerer Runs und automatische Wiederholbarkeit
- [ ] Pruefen, ob weitere CAN-Busse ueber separate Transceiver beobachtet werden koennen

## V0.3 - Verifizierte Signale

- [ ] Experimentell bestaetigte ID-/Bit-Tabelle in `CAN_ANALYSE.md`
- [ ] Signalkatalog mit Bedingungen und Gegenproben
- [ ] Keine automatische Bedeutungszuweisung ohne mehrere reproduzierte Messungen
- [ ] Plausibilitaetspruefung (z. B. Zaehler, Checksummen, Frequenzfenster)

## V0.4 - Ausgaenge (nur mit Hardware-Nachweis)

- [ ] Definierte Treiberstufe fuer GPIO1/GPIO2 (Transistor/MOSFET, Freilauf, Sicherung)
- [ ] Schutz gegen Fehlkonfiguration und unbeabsichtigtes Einschalten
- [ ] Manövrierleuchten und Ambientebeleuchtung erst nach verifizierten Zustaenden
- [ ] Zwei unabhaengige, ueberwachte Ausgaenge
- [ ] Ausgaenge standardmaessig aus, Watchdog und sichere Fehlerzustaende
- [ ] Rechtliche und fahrzeugspezifische Bewertung

## V0.5 - Energiesparen und Aufwecken

- [ ] Verifiziertes Fahrzeug-Ruhesignal (nicht nur CAN-Stille)
- [ ] Geeignete Wake-Hardware (z. B. CAN-Wake-Transceiver oder externe Wake-Schaltung)
- [ ] Kontrollierter Schlaf mit sicheren Ausgaengen
- [ ] Aufwachen ohne Stoerung des Fahrzeug-Ruhezustands
- [ ] Stromverbrauch messen und dokumentieren

## Nicht-Ziele ohne ausdrueckliche Sicherheitsfreigabe

- Aktives Senden von CAN-Frames
- Diagnoseanfragen oder Replay
- Eingriffe in Wegfahrsperre, Tacho, Abgas- oder Sicherheitssysteme
- Steuerung von Fahrzeugfunktionen waehrend der Fahrt
- Automatischer Deep Sleep ohne verifizierte Wake-Hardware
