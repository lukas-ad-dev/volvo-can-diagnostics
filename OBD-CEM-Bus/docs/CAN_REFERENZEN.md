# CAN-Referenzen und Quellenlage

Stand: 03.11.2026. Ziel: **Volvo V90 T8, SPA-Plattform, Modelljahr 2021**.

Diese Datei trennt strikt zwischen:

- **verifizierten Quellen** (Quelle belegt ihre eigene Plattform),
- **Hypothesen** aus anderen Volvo-Plattformen,
- **nicht zugänglichen** oder nur produktbeschreibenden Unterlagen.

**Es gibt nach der hier durchgefuehrten Pruefung keine Quelle, die eine CAN-ID ausdruecklich als V90-2021-SPA-Signal belegt.** Die Datei `config/reference_ids.json` enthaelt die Hypothesen separat; sie werden nicht automatisch als Signalkacheln geladen.

## Quellenuebersicht

| Quelle | URL | Plattform / Baujahr | Was belegt die Quelle? | Vertrauensstatus fuer V90 2021 |
| --- | --- | --- | --- | --- |
| Alfaa123/Volvo-CAN-Gauge | https://github.com/Alfaa123/Volvo-CAN-Gauge | Volvo C30 T5, 2011, P1 | 29-Bit-IDs, 500/125 kbit/s, CEM-Gateway, VIDA-/Broadcast-Experimente | **Nicht uebertragbar**. Andere Plattform; keine SPA-Belegung. |
| Alfaa123 RX List | https://github.com/Alfaa123/Volvo-CAN-Gauge/blob/master/Sniffing/RX%20List.txt | C30 2011, P1 | Empfangsliste mit Perioden und Kommentaren (z. B. Ignition, Door/Lock, Exterior Lights) | **Nur Hypothese**. Keine Bits dokumentiert. |
| olegel/VolvoCan | https://github.com/olegel/VolvoCan | Volvo XC90, P2 (Baujahr im README nicht genannt) | Low-Speed-CAN-Adapter, Listen-Only; konkrete Modul-IDs und Byte-/Bitmasken | **Nicht uebertragbar**. README warnt ausdruecklich: jedes Fahrzeug hat eigene CAN-Modul-IDs. |
| olegel Code | https://github.com/olegel/VolvoCan/blob/master/VolvoCan/include/VolvoCan.h | XC90, P2 | IDs fuer Gearbox, CCM, REM, CEM, SWM; Bitmasken | **Nur Hypothese**. Andere Plattform. |
| realathu/Automotive-CAN-IDs | https://github.com/realathu/Automotive-CAN-IDs | Index (Fork von iDoka/awesome-automotive-can-id) | Links zu Volvo C30, S60, XC70, V60 2015, P3-PIDs, XC90 | **Index only**. Kein V90-2021-SPA-Datensatz. |
| SpeedSignal 332VO03FB | https://manualzz.com/doc/87509182/speedsignal-332vo03fb-owner-s-manual | Produkt fuer V90 2016- (SPA) und weitere SPA-Modelle | Produktbeschreibung: Analogadapter fuer Geschwindigkeit, Klemme 15, Beleuchtung, Rueckwaertsgang | **Keine CAN-IDs**. manualzz lieferte HTTP 403; Suchtreffer belegt nur die Produktbeschreibung. |
| SpeedSignal Produktseite | https://www.speedsignal.de/en | Hersteller | CAN-Adapter, Signalarten (Speed, Terminal 15, Illumination, Reverse) | **Keine IDs**. Produkt-/Herstellerseite. |

## Plattformtrennung

- **P1:** Volvo C30/S40/V50/C70 (ca. 2004-2013). Die Alfaa123-Quellen beziehen sich auf einen C30 T5 2011. Andere Broadcast-IDs, andere Gateway-Struktur.
- **P2:** Volvo S60/S80/V70/XC70/XC90 (ca. 2000-2016). olegel bezieht sich auf einen XC90 dieser Aera. Das README sagt ausdruecklich, dass die CAN-Modul-IDs fahrzeugspezifisch sind.
- **SPA:** Volvo S90/V90/XC90 II/XC60 II/V60 II/S60 III/XC40 (ab 2016/2017). Der V90 T8 2021 gehoert hierzu. Die genannten aelteren Quellen belegen **keine** SPA-IDs.
- Das SpeedSignal-Produkt fuer V90 2016- bestaetigt nur, dass diese Signalarten (Geschwindigkeit, Klemme 15, Beleuchtung, Rueckwaertsgang) im Fahrzeug verfuegbar sind. Es nennt keine CAN-IDs oder Payloads.

## Unbestaetigte Referenzsignale

Diese Eintraege stehen auch in `config/reference_ids.json` und sind ausdruecklich **nicht** fuer den V90 freigegeben. Sie dienen nur als Suchhilfe fuer eigene Messungen.

| CAN-ID | Quelle | Plattform | Vermutete Bedeutung | Byte/Bit | Status |
| --- | --- | --- | --- | --- | --- |
| `0x19E00006` | Alfaa123 Code | C30 2011, P1 | Ignition | Byte 6, `0x40` | unverifiziert, andere Plattform |
| `0x03C3F7FC` | Alfaa123 RX List | C30 2011, P1 | Ignition Status | keine Bitangabe | unverifiziert, andere Plattform |
| `0x0E03D7F8` | Alfaa123 RX List | C30 2011, P1 | Exterior lights symbols | keine Bitangabe | unverifiziert, andere Plattform |
| `0x065373BA` | Alfaa123 RX List | C30 2011, P1 | Door And Lock Status | keine Bitangabe | unverifiziert, andere Plattform |
| `0x1760E008` | Alfaa123 RX List | C30 2011, P1 | Gauge Cluster Speed/Warning Lights | keine Bitangabe | unverifiziert, andere Plattform |
| `0x021204B8` | Alfaa123 RX List | C30 2011, P1 | Turn Signals | keine Bitangabe | unverifiziert, andere Plattform |
| `0x1163F7FC` | Alfaa123 RX List | C30 2011, P1 | Door Sensors | keine Bitangabe | unverifiziert, andere Plattform |
| `0x09C050B8` | Alfaa123 RX List | C30 2011, P1 | Brightness/Mileage/Tacho (Mischsignal) | keine Bitangabe | unverifiziert, andere Plattform |
| `0x1EF00066` | Alfaa123 RX List | C30 2011, P1 | Turns on/off with ignition | keine Bitangabe | unverifiziert, andere Plattform |
| `0x03003028` | olegel Code | XC90 P2 | Gear selector / driving gear | Byte 2, `0x07` / `0x70` | unverifiziert, andere Plattform |
| `0x00E00442` | olegel Code | XC90 P2 | CCM parking button / light meter | Byte 2 `0x40`; Byte 3 low nibble | unverifiziert, andere Plattform |
| `0x01E0522E` | olegel Code | XC90 P2 | REM parking distance | Byte 3, shift 3 | unverifiziert, andere Plattform |
| `0x00617FF8` | olegel Code | XC90 P2 | CEM key position / key in lock | Byte 6, shift 5, `0x04`/`0x03` | unverifiziert, andere Plattform |
| `0x00404066` | olegel Code | XC90 P2 | SWM steering wheel buttons | Byte 6/7, `0x3F` | unverifiziert, andere Plattform |

## Bewusst nicht uebernommene Eintraege

- `0x000FFFFE` aus Alfaa123 ist eine **VIDA-Diagnoseanfrage** (aktiv), keine passive Broadcast-ID. Sie wird nicht verwendet; das Projekt sendet keine Diagnoseanfragen.
- `0x09C050B8` ist ein Mischsignal (Helligkeit, Kilometerstand, Tacho); es ist nicht als einfache boolesche Kachel geeignet.
- Keine der Quellen belegt eine der 13 gewuenschten Funktionen fuer den V90 2021. Deshalb starten alle Signalkacheln als **UNBEKANNT**.

## Konsequenz fuer die Praxis

1. Die Referenz-IDs nicht als Decoder eintragen.
2. Eigene Messungen mit dem Pruefablaeufe durchfuehren: 10 s Grundzustand, Aktion, 10 s Aktion, Gegenaktion, mindestens drei unabhaengige Wiederholungen.
3. Kandidaten mit stabilen Bits und Warnungen (Zaehler/Pruefsumme) sammeln.
4. Nur nach dokumentierter praktischer Pruefung bestaetigen; bestaetigte Definitionen werden getrennt in `config/confirmed_signals.json` gespeichert.
5. Bei fehlenden Frames zuerst Gateway/OBD-Anschlussstelle, Bitrate und CAN H/L pruefen, nicht automatisch einen Firmwarefehler annehmen.

## Sicherheit

Alle Quellen sind nur fuer Bildung/Reverse-Engineering am eigenen Fahrzeug gedacht. Keine aktiven Diagnoseanfragen, keine CAN-Uebertragung, keine Manipulation von Steuergeraeten. Die Firmware bleibt LISTEN_ONLY; die GPIO-Ausgaenge bleiben deaktiviert.
