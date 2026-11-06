# Installation und Inbetriebnahme unter Windows

Diese Anleitung beschreibt den Weg vom MGMT-Server auf einen Windows-Laptop bis zum Flashen des Waveshare ESP32-S3-RS485-CAN. Sie setzt nur grundlegende Computerkenntnisse voraus.

> **Stand 04.11.2026:** Das Board wurde erfolgreich geflasht und ueber USB-CDC getestet. Es wurde noch **kein Fahrzeug** angeschlossen. Alle Schritte zum Fahrzeug sind erst nach Pruefung von `HARDWARE.md` und `CAN_ANALYSE.md` auszufuehren; die konkrete Anleitung steht in `ECHTE_CAN_MESSUNG.md`.

## 1. Projekt vom MGMT-Server auf den Laptop kopieren

Auf dem Windows-Laptop PowerShell oder die Eingabeaufforderung oeffnen. Windows 10/11 bringt einen SSH-Client mit.

```powershell
scp -r user@SERVER:/projekte/Volvo C:\Users\<DeinName>\Documents\
```

`<DeinName>` durch den eigenen Windows-Benutzernamen ersetzen. Alternativ WinSCP verwenden und den Ordner `/projekte/Volvo` auf den Laptop kopieren.

Der Unterordner `.pio` ist nur der Linux-Build-Cache (ca. 58 MB) und kann beim Kopieren ausgelassen werden; PlatformIO baut ihn unter Windows neu. Wer ihn nicht mitkopieren will, kann auf dem MGMT-Server ein Archiv ohne `.pio` erzeugen:

```powershell
ssh user@SERVER "tar -C /projekte -czf - --exclude=Volvo/.pio Volvo" > Volvo.tar.gz
tar -xzf Volvo.tar.gz
```

Der Ordner enthaelt bereits eine lokale `include/secrets.h` mit dem erzeugten WLAN-Passwort. Diese Datei ist nicht fuer eine Veroeffentlichung gedacht. Das Passwort steht zusaetzlich in der Secret-Ablage des MGMT-Servers unter `server/secrets/volvo-can-control-ap.txt`.

Falls `include/secrets.h` fehlt (z. B. weil nur eingecheckte Dateien kopiert wurden):

1. `include/secrets.example.h` nach `include/secrets.h` kopieren.
2. Ein eigenes Passwort mit mindestens 12 Zeichen eintragen.
3. Die Datei nicht in Git oder andere Ablagen ausserhalb des Projekts uebernehmen.

## 2. Entwicklungsumgebung installieren

1. **Visual Studio Code** installieren: <https://code.visualstudio.com/download>
2. In VS Code die Erweiterung **PlatformIO IDE** installieren.
3. VS Code neu starten und in PlatformIO **Open Project** waehlen; den Ordner `Volvo-CAN-Control` oeffnen.
4. PlatformIO installiert beim ersten Build automatisch die benoetigte ESP32-Toolchain. Das kann einige Minuten dauern.

Getesteter Stand: PlatformIO 6.2.0, Plattform `espressif32@8.0.0`, Arduino Core 3.3.12, ArduinoJson 7.4.3.

## 3. Firmware bauen

Im PlatformIO-Terminal (oder in der PlatformIO-Toolbar):

```powershell
pio run -e esp32s3
```

Erwartetes Ergebnis: `SUCCESS`. Die fertige Firmware liegt unter `.pio\build\esp32s3\firmware.bin`.

Die wichtigsten Einstellungen sind bereits in `platformio.ini` hinterlegt:

- ESP32-S3, 16 MB Flash, OPI-PSRAM (`qio_opi`)
- USB-CDC fuer die USB-C-Schnittstelle
- 4-MB-App-Partition mit OTA-Reserve
- ArduinoJson 7.4.3

## 4. ESP32 flashen

1. Waveshare-Board ueber USB-C an den Laptop anschliessen. Ein reines Ladekabel funktioniert nicht; es muss ein Datenkabel sein.
2. Windows erkennt normalerweise einen COM-Port. Falls nicht: anderen USB-Port/Kabel testen, Windows-Update ausfuehren; bei Bedarf die USB-Treiber des Boards pruefen.
3. Flash-Befehl ausfuehren (in der lokalen `.venv`):

```powershell
.venv\Scripts\pio.exe run -e esp32s3 -t upload
```

4. Wenn der Upload nicht startet: **BOOT** gedrueckt halten, **RESET** kurz druecken, **BOOT** loslassen und den Upload erneut starten. Das ist der Download-Modus des ESP32-S3.
5. Serielle Ausgabe ansehen (optional; der lokale Diagnoseserver darf parallel nicht laufen):

```powershell
.venv\Scripts\pio.exe device monitor -b 115200
```

Es wurde bewusst **kein** OTA-Update eingerichtet. Jede neue Firmware wird wieder per USB geflasht.

## 5. WLAN und Weboberflaeche

1. Am Laptop oder Smartphone das WLAN **Volvo-CAN-Control** auswaehlen.
2. Das Passwort aus `include/secrets.h` eingeben (WPA2).
3. Im Browser **http://192.168.4.1** oeffnen. Der ESP vergibt die Standardadresse 192.168.4.1.
4. Falls die Seite nicht erscheint:
   - Mobilfunkdaten am Smartphone kurz deaktivieren.
   - VPN am Laptop deaktivieren.
   - WLAN neu verbinden.
   - Im Browser hart neu laden (`Strg+F5`).
   - Pruefen, ob die AP-Verbindung wirklich zum ESP besteht.

Die Weboberflaeche ist vollstaendig lokal; es werden keine CDN- oder Internet-Ressourcen geladen.

## 6. Demo-Modus ohne Fahrzeug

1. In der Weboberflaeche **Einstellungen** oeffnen.
2. **Demo-Modus** aktivieren und speichern.
3. Oben erscheint ein deutlicher DEMO-Hinweis; jeder Frame traegt die Markierung `DEMO`.
4. Im **CAN-Livemonitor** sollten jetzt regelmaessig synthetische Frames erscheinen.
5. Fuer den **Signalvergleich**:
   - Phase A starten, ca. 16 Sekunden warten, Phase A stoppen.
   - Phase B starten, ca. 16 Sekunden warten, Phase B stoppen.
   - **Vergleich aktualisieren**. Das Demo-Kamera-Bit wechselt alle 15 Sekunden und erzeugt einen sichtbaren Unterschied.
6. Demo-Modus vor dem Anschluss am Fahrzeug wieder deaktivieren.

Ohne Demo-Modus bleibt die Anzeige leer, solange kein CAN-Bus angeschlossen ist. Das ist korrekt und kein Fehler.

## 7. Python-CSV-Collector fuer lange Messungen

Der ESP-Ringpuffer ist bewusst begrenzt. Fuer lange Messungen den Collector auf dem Windows-Laptop verwenden.

1. Python 3 von <https://www.python.org/downloads/windows/> installieren. Beim Setup **Add Python to PATH** aktivieren.
2. Im Projektordner ausfuehren:

```powershell
python tools\volvo_can_collector.py --host 192.168.4.1 --port 81 --output messung.csv
```

3. Mit `Strg+C` beenden. Die CSV-Datei kann direkt in Excel geoeffnet werden.
4. Spalten: `seq`, `timestamp_us`, `can_id`, `can_id_dec`, `extended`, `dlc`, `data_hex`, `demo`, `received_iso`.
5. Der Collector verbindet sich nach einem Verbindungsabbruch automatisch neu und schreibt weiter.

Hinweis: Der TCP-Stream startet mit dem aktuellen Frame. Frames, die waehrend einer Unterbrechung nicht in den Live-Ring passen, koennen fehlen. Der Collector ist fuer kontinuierliche Langzeitmessungen gedacht, ersetzt aber keine lueckenlose Hardwareaufzeichnung.

## 7b. USB-CDC-Logger (empfohlen fuer den ersten Hardwaretest)

Zusaetzlich zum TCP-Collector gibt es einen USB-Logger. Er liest die CAN-Frames direkt ueber den USB-CDC-COM-Port des ESP32, zeigt sie live an und schreibt fortlaufend CSV-Dateien. Fuer den ersten Test ist das der primaere Weg, weil dafuer kein WLAN eingerichtet werden muss.

1. `pyserial` in der lokalen `.venv` installieren (die Batchdatei erledigt das beim ersten Start automatisch):

   ```powershell
   .venv\Scripts\python.exe -m pip install -r tools\requirements.txt
   ```

   `start_logger.bat` erstellt die `.venv` bei Bedarf und installiert `pyserial` automatisch.

2. `start_logger.bat` doppelklicken. Bei mehreren Ports den Espressif-/USB-CDC-Port waehlen.
3. Der Logger legt in `messungen\` automatisch eine Session-CSV und eine Event-Logdatei an. Mit den Tasten `1` bis `10` werden die vorbereiteten Messszenarien als eigene CSV gestartet; `s` stoppt die aktuelle Messung, `q` beendet das Programm.
4. Der PlatformIO-Serial-Monitor darf parallel **nicht** geoeffnet sein; er belegt denselben COM-Port.
5. Messungen vergleichen:

   ```powershell
   python tools\compare_measurements.py messungen\A.csv messungen\B.csv
   ```

Details zu den Szenarien und zum Ablauf stehen in `ERSTER_TEST.md`. Datenverluste und Unterbrechungen werden in der Event-Logdatei und ueber die ESP-Diagnosezeilen `# [USB-STATS] ...` dokumentiert.

## 7c. Lokale Signalerkennung (Windows-Browser)

Fuer die interaktive Identifikation von Signalen gibt es eine lokale Weboberflaeche. Sie laeuft ausschliesslich auf dem Laptop unter `http://127.0.0.1:8765`; das normale Internet-WLAN bleibt nutzbar. Ein ESP-WLAN oder eine USB-Netzwerkemulation ist nicht erforderlich.

1. Auf dem Desktop **Volvo CAN Control** doppelklicken (oder `start_diagnose.bat` ausfuehren). Der Browser oeffnet die Oberflaeche automatisch.
2. Der Server liest denselben USB-CDC-COM-Port wie der USB-Logger. **Nicht gleichzeitig** `start_logger.bat` laufen lassen; immer nur ein Programm darf den COM-Port offenhalten.
3. Fuer einen Test ohne Hardware:

   ```powershell
   start_diagnose.bat --demo
   ```

4. Bei mehreren COM-Ports:

   ```powershell
   start_diagnose.bat --serial-port COM5
   ```

5. Weitere Details, Signalkacheln, Editor, Assistent und Bestaetigung: `SIGNALERKENNUNG.md`.

Die Oberflaeche bietet 14 vorbereitete Signalkacheln (u. a. Rueckwaertsgang, Geschwindigkeit, Licht, Parkkamera, Parksensoren, Tueren, Zentralverriegelung, Zuendung, Komfort/Radio, Ruhezustand), einen Live-CAN-Monitor, einen Bit-/Byte-/Mehrbyte-Editor, einen 10-Sekunden-A/B-Assistenten, eine Ereignis-Zeitleiste, Messungsdateien und CSV-/JSON-Export. Alle fahrzeugspezifischen Signale starten als **UNBEKANNT**; eine Bestaetigung ist erst nach mindestens drei dokumentierten Assistenten-Laeufen mit Gegenaktion moeglich. Es gibt keinen CAN-Sendezpfad.

## 8. Anschluss am Fahrzeug (erst nach Pruefung!)

**Nicht waehrend der Fahrt anschliessen. Fahrzeug abstellen, sicherstellen, dass keine sicherheitsrelevante Aktion ausgeloest wird.**

Vor dem Anschluss:

1. `HARDWARE.md` lesen.
2. Sicherstellen, dass die **120-Ohm-Terminierung** des Boards fuer die geplante Stichleitung deaktiviert ist (Herstellerstandard: NC; Jumper pruefen).
3. CAN H/L korrekt am Fahrzeug-Bus anschliessen; keine Vertauschung. Die Schnittstelle ist galvanisch isoliert.
4. Stromversorgung ueber USB oder den 7-36-V-Eingang gemaess Herstellerdaten; keine ungesicherte Fahrzeugspannung direkt anloeten.
5. **Pinbelegung der realen Board-Revision pruefen:** Die Firmware nutzt die am 04.11.2026 verifizierte Belegung **CAN TX = GPIO15, CAN RX = GPIO16** (RS485: GPIO17/18). Offizieller Schaltplan und `WS_GPIO.h` bestaetigen diese Zuordnung. Vor dem Anschluss trotzdem Durchgang/Silkscreen pruefen; siehe `HARDWARE.md`.
6. Bitrate pruefen: 500 kbit/s ist nur der Standardwert und **nicht** als Volvo-Bitrate bestaetigt. Bei fehlerhaften Frames/Fehlerzaehlern 250 oder 125 kbit/s testen. Nur passiv empfangen; das Geraet sendet nichts.
7. Nach dem Anschluss die Weboberflaeche oeffnen und den CAN-Status beobachten. Bei Bus-Off/Fehlern die Verkabelung und Bitrate pruefen, nicht blind weiterprobieren.

Weitere Analysehinweise stehen in `CAN_ANALYSE.md`.

## 9. Fehlersuche

| Problem | Moegliche Ursache / Loesung |
| --- | --- |
| Kein COM-Port | Kein Datenkabel, Treiber fehlt, USB-Port defekt; BOOT+RESET fuer Download-Modus |
| Upload startet nicht | BOOT gedrueckt halten, RESET, BOOT loslassen, erneut flashen |
| WLAN nicht sichtbar | Board nicht mit Strom versorgt, Firmware nicht gestartet, 2,4-GHz-WLAN am Laptop aktiv? |
| Seite 192.168.4.1 leer | Falsches WLAN, VPN/Mobilfunk aktiv, Browser-Cache; `http://` nicht `https://` verwenden |
| Keine CAN-Frames | Kein Bus angeschlossen, falsche Bitrate, CAN H/L vertauscht, Terminierung falsch |
| Nur Demo-Frames | Demo-Modus ist aktiv; in den Einstellungen deaktivieren |
| Viele TWAI-Fehler | Falsche Bitrate, Stichleitung/Terminierung, Stoerung; keine aktiven Sendungen |
| CSV-Download 409 | Aufzeichnung zuerst stoppen; waehrend der Aufnahme ist kein konsistenter Export moeglich |

## 10. Sicherheitsregeln

- Keine CAN-Sendefunktionen ergaenzen, solange nicht ausdruecklich ein sicherheitsbewertetes Konzept vorliegt.
- Keine Ausgaenge (GPIO1/GPIO2) ohne verifizierte Treiber-/Relais-Hardware und Schutzbeschaltung aktivieren. Die Firmware treibt die Pins nicht (hochohmig), weil LOW-aktive Relais bei LOW einschalten koennten.
- Kein Deep Sleep aktivieren, solange kein verifiziertes Wake-Signal und keine geeignete Wake-Hardware vorhanden sind.
- Keine fremden Fahrzeuge, keine Manipulation, keine Umgehung von Wegfahrsperren oder sicherheitsrelevanten Funktionen.
