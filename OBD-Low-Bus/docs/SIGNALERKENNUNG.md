# Signalerkennung: lokale Windows-Oberflaeche

Diese Anleitung beschreibt die lokale Diagnoseoberflaeche fuer die interaktive Identifikation von CAN-Signalen. Sie liest ausschliesslich ueber den USB-CDC-Collector. Es gibt **keinen** CAN-Sendezpfad, keine Diagnoseanfrage und keine Steuergeraeteveraenderung.

## Start

1. Windows-Laptop mit dem ESP32 ueber USB-C verbinden.
2. Auf dem Desktop **Volvo CAN Control** doppelklicken. Alternativ `start_diagnose.bat` ausfuehren.
3. Der Starter erkennt den ESP-Port, startet den Server und oeffnet automatisch **http://127.0.0.1:8765**.
4. Der Server bindet nur an `127.0.0.1`; das normale Internet-WLAN des Laptops bleibt unveraendert. Kein ESP-WLAN notwendig, keine USB-Netzwerkemulation.

Optionen:

```powershell
start_diagnose.bat --demo
start_diagnose.bat --serial-port COM5
start_diagnose.bat --port 8765
```

`--demo` erzeugt synthetische Frames in einem separaten Ordner `messungen\demo\`. DEMO-Daten werden nie mit echten Daten gemischt; der Server ignoriert DEMO-Frames im Serialmodus. Bestaetigungen mit DEMO-Evidenz sind gesperrt.

Benoetigt wird Python 3 mit `pyserial`; die Batchdatei erstellt bei Bedarf eine lokale `.venv` und installiert die Abhaengigkeiten. Manuell:

```powershell
.venv\Scripts\python.exe -m pip install -r tools\requirements.txt
```

## Live-CAN-Monitor

Der Reiter **Live-CAN-Monitor** zeigt alle empfangenen Rohframes:

- Zeitstempel, Sequenz, CAN-ID (Hex), Standard/Extended, DLC und Datenbytes
- Nachrichten pro Sekunde gesamt und pro CAN-ID
- Filter nach CAN-ID, Datenbytes und Frame-Typ (STD/EXT)
- Pause, Leeren und Anzeige-Luecken
- Aufzeichnung starten/stoppen sowie **Session-CSV**, **Roh-JSONL** und **Messdateien**

Die Aufzeichnung schreibt unabhaengig von den Anzeigefiltern alle Frames in die Session-CSV. Diagnosemeldungen des ESP stehen getrennt in der Ereignis-Zeitlinie und im Event-Log; sie werden nicht als CAN-Frames angezeigt. DEMO-Frames sind in der Tabelle und im Kopf deutlich markiert.

## LED-Bedeutung

| LED | Bedeutung |
| --- | --- |
| GRUEN | Signal ist bestaetigt und EIN |
| GRAU | Signal ist bestaetigt und AUS |
| GELB | UNBEKANNT / Kandidat / noch nicht praktisch bestaetigt |
| ROT | Daten ungueltig, veraltet oder verloren |

Alle 14 Kacheln (inkl. Tueren, Zentralverriegelung, Zuendung, Komfort/Radio und Ruhezustand) starten als **UNBEKANNT**, weil keine V90-2021-SPA-ID verifiziert ist. Das ist beabsichtigt. Die Rohwerte einer Kandidatenkachel werden angezeigt, aendern aber die gelbe LED nicht.

## Signal-Editor

Eine Kachel auswaehlen und **Bearbeiten** waehlen. Felder:

- **CAN-ID** hexadezimal, **Standard/Extended**, **DLC**
- **Byteposition** (0-basiert; Byte 0 = erstes Datenbyte)
- **Laenge** in Bytes (1-8), **Little/Big Endian**
- **Bitmaske**, **Vergleichswert**, **Invertierung**
- **Timeout** in ms
- Optional **Wertebereich min/max**, **Faktor**, **Offset**
- Notizen

Beispiele:

- Ein Bit: Byte 2, Laenge 1, Bitmaske `0x10`, Vergleichswert `0x10`.
- Ein 16-Bit-Wert: Byte 2, Laenge 2, Little Endian, Bitmaske `0xFFFF`, Wertebereich `0..300`, Faktor `0.1` fuer km/h.

Speichern erzeugt hoechstens einen **Kandidaten**. Eine geaenderte Definition setzt eine alte Bestaetigung zurueck und verwirft die bisherige Evidenz. Der Editor sendet nichts an das Fahrzeug; er schreibt nur `config/signals.json`.

## Messassistent

Ziel: Ein Bit finden, das sich bei einer definierten Aktion reproduzierbar aendert.

1. **Grundzustand starten.** 10 Sekunden werden aufgenommen. Fahrzeugzustand nicht veraendern.
2. **Aktion markieren.** Die Aktion ausfuehren (z. B. Rueckwaertsgang einlegen) und im Feld die Bezeichnung eintragen.
3. **Aktionsphase.** Weitere 10 Sekunden werden aufgenommen.
4. **Auswerten.** Kandidaten erscheinen mit ID, Byte, Bit, A/B-Wert, Score und Warnungen.
5. **An Kachel binden.** Kandidat und Zielkachel auswaehlen.
6. **Gegenaktion.** Neuen Lauf mit der Gegenaktion starten (z. B. Rueckwaertsgang AUS) und denselben Kandidaten binden.
7. **Wiederholen.** Mindestens drei unabhaengige Laeufe mit mindestens zwei unterschiedlichen Aktionsbezeichnungen.

Der Assistent markiert Warnungen:

- **andere Bits wechseln**: moeglicher Zaehler, Pruefsumme oder Mischsignal.
- **Byte enthaelt wechselnde Bits**: der Kandidat ist weniger vertrauenswuerdig.
- **wenige Frames**: Score sinkt.
- **DEMO-Daten**: Bestaetigung gesperrt.

**Korrelation allein ist keine Bestaetigung.** Ein Kandidat bleibt gelb, bis die praktische Pruefung dokumentiert ist.

## Live-Test und Zeitlinie

Unter **Live-Test** eine Kachel auswaehlen. Angezeigt werden:

- aktueller Zustand und Rohwert
- letzte Aktualisierung, Empfangshaeufigkeit
- Zustandswechsel als `P: AUS -> R: EIN`
- zugeordnete Messungen

Mit **Aktion EIN/AUS markieren** werden Benutzer-Ereignisse in die Zeitlinie geschrieben. Die Zeitlinie enthaelt Benutzer-Markierungen, Signalwechsel, Verbindungsereignisse und Messungsstarts.

## Messungen

Die 10 Szenarien stehen im Auswahlfeld:

1. Fahrzeug verriegelt
2. Fahrzeug entriegeln
3. Fahrertuer oeffnen
4. Zuendung aktivieren
5. Rueckwaertsgang einlegen
6. Abblendlicht einschalten
7. Fernlicht einschalten
8. Parkkamera manuell aktivieren
9. Radio bei ausgeschaltetem Fahrzeug weiterlaufen lassen
10. Fahrzeug verriegeln und CAN-Aktivitaet beobachten

Jede Messung wird als eigene CSV gespeichert. Die Session-CSV laeuft unabhaengig davon weiter und enthaelt alle Frames; die GUI-Filter beeinflussen die Rohaufzeichnung nicht.

## Bestaetigung und Speicherung

Statuswerte: `UNBEKANNT`, `KANDIDAT`, `IN PRUEFUNG`, `BESTAETIGT`, `VERWORFEN`.

Die Bestaetigung ist nur moeglich, wenn:

- mindestens **3 unabhaengige Assistenten-Laeufe** mit derselben Bitdefinition vorliegen,
- mindestens **2 unterschiedliche Aktionsbezeichnungen** vorkommen (z. B. EIN/AUS),
- keine DEMO-Evidenz enthalten ist,
- die Checkliste zur praktischen Gegenprobe bestaetigt wird,
- eine Bestaetigungsnotiz eingetragen ist.

Bestaetigte Definitionen werden getrennt gespeichert:

- `config/confirmed_signals.json`
- `config/generated/esp32_signals.json` (Decoder-Konfiguration fuer spaetere Firmware-Integration)

`config/signals.json` enthaelt alle Kacheln und Kandidaten. `config/reference_ids.json` enthaelt ausschliesslich unverifizierte Fremdplattform-Hypothesen.

## Export und Datenverlust

Unter **Export & Status**:

- Session-CSV, Roh-JSONL, Roh-JSON
- Events-JSONL, Events-JSON
- bestaetigte Signale und ESP32-Generat
- Messdateien als CSV/JSON
- Zaehler: Frames, DEMO, Parse-Fehler, Reconnects, ESP-USB-Statistik (`tx`, `dropped`, `txerr`, Queue)

Die Rohdaten werden unabhaengig von der GUI gespeichert. Bei fehlenden Frames zeigt die Oberflaeche einen Hinweis auf Gateway, OBD-Anschlussstelle, Bitrate und CAN H/L; sie behauptet nicht automatisch einen Firmwarefehler.

## Referenzen

`CAN_REFERENZEN.md` dokumentiert die geprueften Quellen und die Plattformtrennung P1/P2/SPA. Die Referenz-IDs sind **nicht** als V90-2021-Definitionen freigegeben und werden nicht automatisch geladen.

## Sicherheit

- CAN ausschliesslich `LISTEN_ONLY`.
- Keine Diagnoseanfragen, keine CAN-Uebertragung, keine Injektion.
- Keine Steuergeraeteveraenderung.
- GPIO1/GPIO2 bleiben hochohmig und deaktiviert.
- Keine Hardware flashen und keine Fahrzeugverbindung herstellen, solange die Pin-/Terminierungspruefung nicht abgeschlossen ist.
