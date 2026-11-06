# Demo-Daten

`demo_frames.ndjson` enthaelt 100 synthetische CAN-Frames. Jede Zeile ist ein JSON-Objekt mit `"demo": true`. Die IDs und Nutzdaten sind frei erfunden und haben **keine Volvo-Bedeutung**.

Die Datei wird mit folgendem Befehl neu erzeugt:

```bash
python3 tools/generate_demo_data.py
```

Format einer Zeile:

```json
{"type":"can","seq":1,"timestamp_us":0,"id":416,"id_hex":"0x1A0","extended":false,"dlc":8,"data":"010000005A000000","demo":true}
```

Verwendung:

- Als Anschauungsmaterial fuer das NDJSON-Format des TCP-Streams.
- Zum Testen des Python-Collectors mit einem eigenen kleinen TCP-Server.
- Zum Vergleichen mit den synthetischen Frames aus dem Demo-Modus der Firmware (die Firmware erzeugt eigene, ebenfalls klar markierte Demo-Frames).

Nicht als echte Fahrzeugdaten verwenden oder in Analysen mit realen Messungen mischen. Der Demo-Modus der Firmware ist davon unabhaengig und immer sichtbar als `DEMO` gekennzeichnet.
