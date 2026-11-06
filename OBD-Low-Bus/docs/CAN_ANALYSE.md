# CAN-Analyse: Vorgehen und spaetere ID-Zuordnung

## Ausgangslage

Dieses Projekt beobachtet CAN-Frames passiv. Es behauptet **nicht**, dass eine bestimmte CAN-ID fuer Geschwindigkeit, Licht, Kamera oder eine andere Funktion steht. Solche Zuordnungen entstehen erst durch wiederholte, kontrollierte Messungen und Gegenproben.

## Hardwarebelegung

Die Firmware verwendet die am 04.11.2026 anhand des offiziellen Schaltplans und von `WS_GPIO.h` bestaetigte Belegung **CAN TX = GPIO15, CAN RX = GPIO16**; RS485 liegt auf GPIO17/18 und wird nicht benutzt. Vor dem Anschluss am Fahrzeug die reale Board-Revision optisch pruefen; Details in `HARDWARE.md`. Die zentrale Aenderungsstelle ist `lib/volvo_core/include/volvo_core/hardware_pins.h`.

Der Standardwert **500 kbit/s ist nicht als Volvo-Bitrate bestaetigt**. Er ist nur der Startwert, weil viele Fahrzeug-CAN-Busse mit 500 kbit/s arbeiten. Wenn keine plausiblen Frames ankommen oder der TWAI-Status Fehler zeigt, zuerst 250 kbit/s, dann 125 kbit/s testen. Immer nur passiv empfangen; das Geraet sendet nichts.

## Wichtige Einschraenkungen

- Der Volvo V90 T8 (SPA) hat mehrere CAN-Busse und ein zentrales Gateway. Der OBD-Anschluss oder ein einzelner Bus liefert nicht zwingend alle Nachrichten.
- Die gleiche CAN-ID kann auf verschiedenen Bussen unterschiedliche Bedeutung haben.
- Viele IDs sind Zaehler, Statusbits oder periodische Lebenszeichen. Ein einzelner Frame beweist keine Funktion.
- Ein Bitwechsel kann eine Anzeige, einen Zaehler, eine Checksumme oder Rauschen darstellen.
- Ein verschwundener Frame kann auch an einer geaenderten Buslast, einem Gateway-Filter oder einer abgeschalteten ECU liegen.
- Nach dem Fahrzeugschlaf koennen IDs fehlen, ohne dass eine Funktion aus ist.

## Messphasen A/B

Ziel: Zwei vergleichbare Zustaende unterscheiden. Die Software ermoeglicht zwei Phasen mit demselben Datenmodell.

1. **Gleiche Bedingungen herstellen:** Fahrzeugzustand, Zuendung, Tueren, Klima, Licht, Kamera und Wartezeit vor der Messung identisch halten.
2. **Phase A starten**, eine definierte Zeit warten (z. B. 30-60 s), **Phase A stoppen**.
3. Die zu untersuchende Aktion ausfuehren. Beispiel: Kamera ausschalten, warten, bis sich der Zustand stabilisiert hat.
4. **Phase B starten**, dieselbe Dauer warten, **Phase B stoppen**.
5. **Vergleich aktualisieren** und die Ergebnisse exportieren.
6. Messung mindestens zweimal wiederholen. Nur reproduzierbare Unterschiede sind interessant.
7. Gegenprobe: Aktion in umgekehrter Reihenfolge (B vor A) wiederholen.

Wichtig: Phase A und B duerfen nicht gleichzeitig laufen. Die Firmware verhindert das.

## Messungen mit dem USB-Logger

Fuer den ersten Hardwaretest wird der USB-CDC-Logger verwendet (`ERSTER_TEST.md`). Er speichert eine fortlaufende Session-CSV und zusaetzlich benannte Einzelmessungen. Die Tasten `1` bis `10` entsprechen den vorbereiteten Szenarien:

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

Jede Einzelmessung wird als eigene CSV gespeichert. Zwei Messungen lassen sich vergleichen mit:

```bash
python tools/compare_measurements.py messung_a.csv messung_b.csv --format table
```

Das Skript markiert neue/verschwundene IDs, geaenderte Bytes/Bits, Variabilitaet und Frequenzaenderungen. Es ordnet keine Fahrzeugfunktion zu. DEMO-Frames werden standardmaessig ignoriert.

## Lokale Signalerkennung

Zusaetzlich zu den Messdateien gibt es eine lokale Windows-Oberflaeche (`SIGNALERKENNUNG.md`, Start mit `start_diagnose.bat`). Sie fuehrt durch den A/B-Pruefablaeufe:

1. 10 s Grundzustand,
2. Aktion markieren,
3. 10 s Aktionsphase,
4. Kandidaten nach stabilen Bits sortieren,
5. Kandidat an eine Signalkachel binden,
6. Gegenaktion und mindestens drei unabhaengige Wiederholungen,
7. erst dann bestaetigen.

Zaehler, Pruefsummen und andere wechselnde Bits werden als Warnung markiert und senken den Score. Neue/verschwundene IDs werden separat angezeigt. Unverifizierte Fremdplattform-IDs stehen nur in `CAN_REFERENZEN.md` und `config/reference_ids.json`; sie werden nicht automatisch geladen.

## Was der Vergleich anzeigt

- **Neu in Phase B:** IDs, die nur in B empfangen wurden.
- **Nur in Phase A:** IDs, die in B fehlen.
- **Gemeinsame IDs mit Aenderungen:** Unterschiede im zuletzt gesehenen Datenfeld, in einzelnen Bytes/Bits und in der Empfangshaeufigkeit.
- **Variabilitaet:** Bits, die innerhalb einer Phase unterschiedliche Werte hatten. Solche Bits sind ohne weitere Analyse nicht als stabiler Zustand geeignet.
- **Frequenzaenderung:** markiert ab 20 % relativer Aenderung und mindestens 0,2 Hz absolut. Das ist eine Heuristik, kein Beweis.

Die Anzeige ist bewusst vorsichtig formuliert. Sie ersetzt keine Signaldefinition und keine Fahrzeugdokumentation.

## Empfohlenes Vorgehen fuer neue IDs

1. Zuerst die komplette Busaktivitaet fuer 5-10 Minuten im Stand beobachten (Phase ohne Aktion).
2. Periodische IDs mit stabiler Frequenz und kurzer DLC notieren.
3. Eine einzelne Fahrzeugfunktion aendern, am besten mit klarer, reproduzierbarer Bedienung.
4. A/B-Vergleich durchfuehren und die Kandidaten notieren.
5. Kandidaten in mehreren Runs mit unterschiedlichen Ausgangszustaenden bestaetigen.
6. Erst dann eine Bedeutung in die Tabelle unten eintragen, mit Datum, Fahrzeugzustand und Reproduktionsschritten.
7. Bei sicherheitsrelevanten Funktionen (Bremsen, Lenkung, Antrieb, Airbags) keine experimentellen Eingriffe; nur beobachten.

## Kandidatentabelle (Vorlage)

Die Tabelle absichtlich leer. Eintraege erst nach reproduzierbaren Messungen ergaenzen.

| CAN-ID | Ext. | DLC | Frequenz | A-Daten | B-Daten | Aenderung | Kandidat fuer | Bestaetigt am | Bedingungen / Notizen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |

## Messdaten ablegen

- Kurze Messungen: CSV/JSON ueber die Weboberflaeche herunterladen (Aufzeichnung vorher stoppen).
- Lange Messungen: Python-Collector auf Windows verwenden.
- Dateinamen mit Datum, Fahrzeugzustand und Aktion versehen, z. B. `2026-11-03_kamera-aus-an_phase-a.csv`.
- Vergleichs-Exporte (`volvo-can-vergleich.csv/json`) gemeinsam mit den Rohdaten ablegen.
- Keine personenbezogenen Daten oder Standortdaten in oeffentliche Ablagen uebernehmen.

## Demo-Daten

Die IDs in `data/demo/` und im Demo-Modus sind **frei erfunden**. Sie dienen nur der UI- und Logiktests. Sie haben keine Volvo-Bedeutung. Das Demo-Kamera-Bit wechselt alle 15 Sekunden, damit der Signalvergleich geuebt werden kann.

## Recht und Sicherheit

Nur autorisierte Diagnose am eigenen Fahrzeug. Keine Manipulation von Wegfahrsperre, Tacho, Abgas- oder Sicherheitssystemen. Keine Eingriffe waehrend der Fahrt. Die Software sendet in V0.1 nichts auf den CAN-Bus, aber die Verkabelung und Terminierung muessen trotzdem fachgerecht sein.
