# Erster Hardwaretest - 04.11.2026

Ziel: Waveshare ESP32-S3-RS485-CAN per USB-C am Windows-Laptop, CAN des Volvo V90 T8 **nur passiv** empfangen, live anzeigen und als CSV aufzeichnen. Es wird **nichts** auf den CAN-Bus gesendet, keine Diagnoseanfrage gestellt und kein Ausgang aktiviert.

> **Vor dem Anschluss lesen:** Die Firmware verwendet die am 04.11.2026 verifizierte Belegung **CAN TX = GPIO15, CAN RX = GPIO16** (RS485: GPIO17/18). Offizieller Schaltplan und `WS_GPIO.h` bestaetigen diese Zuordnung. Vor dem Anschluss am Fahrzeug die reale Board-Revision trotzdem optisch pruefen (Silkscreen/Durchgang). Bei Unklarheit **nicht anschliessen**. Die zentrale Aenderungsstelle ist `lib/volvo_core/include/volvo_core/hardware_pins.h`.

## 1. Windows vorbereiten

1. Projekt vom MGMT-Server kopieren (siehe `INSTALLATION.md`):

   ```powershell
   scp -r user@SERVER:/projekte/Volvo C:\Users\<DeinName>\Documents\
   ```

2. Python 3 von <https://www.python.org/downloads/windows/> installieren; **Add Python to PATH** aktivieren.
3. `include/secrets.h` pruefen. Das WLAN-Passwort steht dort und in `/secrets/volvo-can-control-ap.txt`.
4. VS Code + PlatformIO IDE installieren und den Ordner `Volvo` oeffnen.
5. `pyserial` wird von `start_logger.bat` automatisch installiert; manuell:

   ```powershell
   python -m pip install pyserial
   ```

## 2. Firmware flashen

1. **Alle Programme schliessen, die den COM-Port offenhalten** (PlatformIO Serial Monitor, PuTTY, Arduino IDE).
2. USB-C-Datenkabel anschliessen (kein reines Ladekabel).
3. Bauen und flashen:

   ```powershell
   pio run -e esp32s3
   pio run -e esp32s3 -t upload
   ```

4. Falls der Upload nicht startet: **BOOT** halten, **RESET** kurz druecken, **BOOT** loslassen, Upload erneut starten.
5. Optionaler Funktionstest mit Serial Monitor:

   ```powershell
   pio device monitor -b 115200
   ```

   Danach den Monitor **wieder schliessen**. Der USB-Logger und der Serial Monitor koennen den COM-Port nicht gleichzeitig nutzen.

## 3. Hardware vor dem Fahrzeug pruefen

- [ ] Board ist die erwartete Revision; CAN-Pins **am realen Board** verifiziert (GPIO15/16 gemaess Schaltplan und WS_GPIO.h).
- [ ] CAN-Terminierung **deaktiviert**: Jumperstellung pruefen; spannungsfrei darf zwischen CAN H und CAN L **nicht** etwa 120 Ohm messen.
- [ ] OBD2-Pigtail: **Pin 6 = CAN-H**, **Pin 14 = CAN-L**. Nur diese beiden Signale anschliessen.
- [ ] Board wird ueber USB-C versorgt; keine ungesicherte Fahrzeugspannung anloeten.
- [ ] Fahrzeug steht, keine Fahrt, keine sicherheitsrelevanten Aktionen.
- [ ] Keine Relais/LEDs an GPIO1/GPIO2 angeschlossen.

**Gateway-Hinweis:** Der Volvo-Gateway kann den passiven Zugriff auf interne CAN-Nachrichten einschraenken. OBD2 liefert moeglicherweise nur einen Teil des Busses. Das ist kein Fehler der Firmware; die Einschraenkung wird dokumentiert, nicht umgangen.

## 4. USB-Logger starten

1. `start_logger.bat` doppelklicken.
2. Falls mehrere COM-Ports vorhanden sind, den Espressif-/USB-CDC-Port waehlen.
3. Der Logger legt automatisch an:
   - `messungen\session_<Datum-Uhrzeit>.csv` - fortlaufende Sitzung
   - `messungen\session_<Datum-Uhrzeit>_events.log` - Verbindung, Diagnose, Unterbrechungen
4. Live-Anzeige beobachten. CAN-Zeilen sind JSON; Diagnosezeilen beginnen mit `#`.
5. Wenn kein Port gefunden wird: USB-Kabel pruefen, Board neu verbinden, alle anderen seriellen Programme schliessen.
6. **Erst danach das OBD2-Pigtail am Fahrzeug anschliessen** (Fahrzeug aus, siehe Abschnitt 3). So ist die Session von Anfang an offen und die USB-Queue enthaelt keine alten Frames.

**Bitrate:** Standard ist 500 kbit/s, ausdruecklich **nicht** als Volvo-Wert bestaetigt. Wenn keine plausiblen Frames kommen, im WLAN `Volvo-CAN-Control` mit der Weboberflaeche `http://192.168.4.1` die Bitrate auf 250 oder 125 kbit/s umstellen. Der USB-Logger bleibt dabei verbunden.

## 5. Messungen markieren (Szenarien 1-10)

Der Logger laeuft bereits und die OBD2-Verbindung ist hergestellt. Vor jeder Aktion einige Sekunden Vorlauf aufzeichnen.

Im Logger-Fenster eine Zahl druecken; die Messung startet sofort und wird als eigene CSV gespeichert. Mit `s` stoppen. Jede Messung einzeln wiederholen.

| Taste | Szenario | Empfohlene Aktion |
| --- | --- | --- |
| `1` | Fahrzeug verriegelt | 10-20 s im verriegelten Zustand aufzeichnen |
| `2` | Fahrzeug entriegeln | Taste starten, dann entriegeln |
| `3` | Fahrertuer oeffnen | Tuer oeffnen, kurz warten, stoppen |
| `4` | Zuendung aktivieren | Zuendung einschalten, Zustand stabilisieren lassen |
| `5` | Rueckwaertsgang einlegen | Nur im Stand; Gang einlegen, nicht fahren |
| `6` | Abblendlicht einschalten | Licht ein, kurz warten |
| `7` | Fernlicht einschalten | Fernlicht ein, kurz warten |
| `8` | Parkkamera manuell aktivieren | Kamera manuell starten |
| `9` | Radio bei ausgeschaltetem Fahrzeug | Radio laufen lassen, Fahrzeug aus |
| `10` | Fahrzeug verriegeln und CAN-Aktivitaet beobachten | Verriegeln, laenger beobachten |

Weitere Befehle:

- `r <Name>` - freie Messung starten, z. B. `r kamera_an`
- `s` - laufende Messung stoppen
- `l` - Messdateien anzeigen
- `i` - Status (Session-Frames, Messung, Anzeige-Verwuerfe)
- `q` - beenden und Dateien schliessen

Hinweise:

- Vor und nach jeder Aktion einige Sekunden aufzeichnen; Aktion nicht waehrend eines einzelnen Frames ausloesen.
- Jede Messung mindestens zweimal wiederholen.
- Keine Bedeutung aus einer einzelnen Messung ableiten.
- Die Session-CSV laeuft immer weiter; die Szenario-Dateien sind die einzelnen Messungen.

## 6. Messungen auswerten

Zwei Messdateien vergleichen:

```powershell
python tools\compare_measurements.py messungen\20261104-..._01_fahrzeug_verriegelt.csv messungen\20261104-..._02_fahrzeug_entriegeln.csv
```

Alternativ als JSON oder CSV:

```powershell
python tools\compare_measurements.py A.csv B.csv --format json --output vergleich.json
python tools\compare_measurements.py A.csv B.csv --format csv --output vergleich.csv
```

Das Skript zeigt neue/verschwundene CAN-IDs, geaenderte Bytes/Bits, Variabilitaet und Frequenzaenderungen. **Es ordnet keine Bedeutung zu.** DEMO-Frames werden standardmaessig ignoriert; `--include-demo` nur fuer Tests verwenden.

## 7. Datenverluste und Unterbrechungen

- Die Event-Datei protokolliert Verbindungsaufbau, Abbruch, Wiederverbindung und ESP-Diagnosezeilen.
- Der ESP sendet regelmaessig `# [USB-STATS] tx=... dropped=... txerr=... queue=.../...`.
- `dropped` im ESP bedeutet: USB-Queue voll oder USB nicht bereit; die Frames fehlen in der Aufzeichnung.
- `txerr` bedeutet: USB-Schreibfehler.
- Im Web-Dashboard gibt es eine Karte **USB-Logger** mit TX / verworfen / Fehlern und Queue-Stand.
- Die Live-Anzeige kann bei sehr hoher Buslast Zeilen auslassen, damit die CSV-Aufzeichnung nicht blockiert. Die CSV wird weiter geschrieben.

## 8. Sicherheit

- TWAI laeuft ausschliesslich im Modus `LISTEN_ONLY`; kein Senden, keine ACKs, keine Diagnoseanfragen.
- Keine Fahrzeugsteuerung, kein Replay, kein Gateway.
- GPIO1/GPIO2 bleiben hochohmig und werden nicht angesteuert; keine Relais anschliessen.
- Der Energiesparmodus bleibt deaktiviert; USB-Logger und USB-Verbindung bleiben aktiv.
- Nicht waehrend der Fahrt anschliessen. Nur autorisierte Diagnose am eigenen Fahrzeug.
- Bei Bus-Off/Fehlern: Verkabelung, Terminierung und Bitrate pruefen; nicht blind weiterprobieren.

## 8b. Lokale Signalerkennung (optional)

Wenn nach dem ersten Empfang Signale identifiziert werden sollen:

```powershell
start_diagnose.bat
```

Der Browser oeffnet `http://127.0.0.1:8765`. Das normale Internet-WLAN bleibt nutzbar. Die Oberflaeche liest denselben COM-Port; `start_logger.bat` und `start_diagnose.bat` duerfen **nicht gleichzeitig** laufen. Details: `SIGNALERKENNUNG.md`; Quellen und unverifizierte Referenzen: `CAN_REFERENZEN.md`.

## 9. Was heute noch nicht getestet werden kann

- Echtes Flashen auf das Waveshare-Board
- WLAN-AP und Browser auf dem ESP
- USB-CDC-Enumeration unter Windows
- Reale CAN-Kommunikation, Bitrate und Terminierung
- Reale PSRAM-Erkennung
- Reale GPIO-Revision (PDF und Vorgabe widersprechen sich)
- Verhalten bei Bus-Off am Fahrzeug

Der Build, die Logik-Tests, die NDJSON-Formatierung, der Windows-Logger mit simulierten seriellen Frames und der Vergleich zweier Messungen wurden auf dem MGMT-Server getestet. Details: `docs/TESTBERICHT.md`.
