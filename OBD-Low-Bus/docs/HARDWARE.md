# Hardware: Waveshare Industrial ESP32-S3-RS485-CAN

## Geraet

Verwendet wird das Waveshare **ESP32-S3-RS485-CAN** im kleinen Hutschienengehaeuse (Onboard-Antenne). Die Variante **-U** hat eine externe Antenne; die Firmware ist identisch.

Herstellerquellen:

- Produktseite: <https://docs.waveshare.com/ESP32-S3-RS485-CAN>
- Arduino/Beispiele: <https://docs.waveshare.com/ESP32-S3-RS485-CAN/Arduino>
- Ressourcen/Schaltplan: <https://docs.waveshare.com/ESP32-S3-RS485-CAN/Resources-And-Documents>
- Beispielcode: <https://files.waveshare.com/wiki/ESP32-S3-RS485-CAN/ESP32-S3-RS485-CAN-Demo.zip>
- Schaltplan: <https://files.waveshare.com/wiki/ESP32-S3-RS485-CAN/ESP32-S3-RS485-CAN-Schematic.pdf>

## Technische Daten (Herstellerangaben)

| Merkmal | Wert |
| --- | --- |
| Mikrocontroller | ESP32-S3R8 (Xtensa LX7, 240 MHz, 2,4-GHz-WLAN, BLE 5) |
| Flash | 16 MB |
| PSRAM | ESP32-S3R8-Namensschema: 8 MB; im PlatformIO-Profil als OPI-PSRAM aktiviert |
| USB | USB-C, 5 V, Daten/Firmware/Seriell |
| Spannungsversorgung | USB 5 V oder Klemme 7-36 V DC |
| CAN | Isolierte CAN-Schnittstelle, Klemme H/L, TVS-Schutz |
| RS485 | Isolierte RS485-Schnittstelle, Klemme A+/B-, TVS-Schutz |
| Terminierung CAN | 120 Ohm reserviert, standardmaessig **NC**, per Jumper aktivierbar |
| Terminierung RS485 | 120 Ohm reserviert, standardmaessig **NC**, per Jumper aktivierbar |
| Gehaeuse | Hutschiene, ca. 91,6 x 23,3 x 58,7 mm |
| Bedienelemente | BOOT- und RESET-Taste |
| RTC | PCF85063 (in dieser Version nicht genutzt) |

Die Angabe "8 MB PSRAM" ergibt sich aus der im Herstellerdokument genannten ESP32-S3R8-Variante. Am 04.11.2026 am realen Board bestaetigt: ESP32-S3 rev. v0.2, 16 MB Flash, 8 MB eingebettetes PSRAM; die Firmware alloziert den 16.384-Frame-Puffer erfolgreich im PSRAM. `ESP.getFreePsram()` liefert in diesem Arduino-Core-Build trotzdem 0, weil `psramFound()` falsch meldet; `heap_caps` zeigt 8 MB gesamt und ca. 7,8 MB frei. Bei fehlendem PSRAM faellt die Firmware automatisch auf einen kleineren internen Aufzeichnungspuffer zurueck.

## Anschluesse und Pins

| Funktion | Pin / Klemme | Verwendung in V0.1 |
| --- | --- | --- |
| CAN TX (TWAI) | **GPIO15** | konfiguriert, im LISTEN_ONLY nicht zum Senden genutzt |
| CAN RX (TWAI) | **GPIO16** | Empfang |
| RS485 TX | **GPIO17** | nicht verwendet |
| RS485 RX | **GPIO18** | nicht verwendet |
| RS485 DE/EN | GPIO21 | nicht verwendet |
| Externer Ausgang 1 | GPIO1 (SH1.0) | vorbereitet, hochohmig (INPUT), nicht angesteuert |
| Externer Ausgang 2 | GPIO2 (SH1.0) | vorbereitet, hochohmig (INPUT), nicht angesteuert |
| CAN-Bus | Klemme H/L | passiv empfangen |
| Stromversorgung | Klemme 7-36 V oder USB-C | 5 V USB oder Fahrzeugspannung im erlaubten Bereich |
| USB-C | Daten/Firmware/Seriell | Flashen und Serial Monitor |

### Pin-Belegung (verifiziert am 04.11.2026)

Die Zuordnung wurde erneut gegen die offiziellen Waveshare-Quellen geprueft:

- Schaltplan `ESP32-S3-RS485-CAN-Schematic.pdf`: CAN-Transceiver U8 (TJA1051) haengt an den Netzen `TXD2`/`RXD2`; RS485-Transceiver U7 (SP3485EN) an `TXD1`/`RXD1`.
- Demo `ESP32-S3-RS485-CAN-Demo.zip`, Datei `WS_GPIO.h`: `TXD2 = 15`, `RXD2 = 16`, `TXD1 = 17`, `RXD1 = 18`.
- Damit gilt bestaetigt: **CAN TX = GPIO15, CAN RX = GPIO16; RS485 TX = GPIO17, RS485 RX = GPIO18.**

Die fruehere Annahme CAN TX=GPIO17/RX=GPIO18 war falsch und wurde in der Firmware korrigiert. Die zentrale Aenderungsstelle ist `lib/volvo_core/include/volvo_core/hardware_pins.h`; `static_asserts` und `tools/check_hardware_pins.py` schuetzen die bestaetigte Belegung.

Vor dem Anschluss am Fahrzeug trotzdem die reale Board-Revision optisch pruefen (Silkscreen, Durchgang): Der Schaltplan beschreibt die aktuelle Standardrevision. Wenn das gelieferte Board abweicht, nicht anschliessen und die Belegung erneut klaeren.

GPIO47 aus dem Beispiel ist **nicht** die Klemme GPIO1/GPIO2; die externen Klemmen sind GPIO1 und GPIO2 am SH1.0-Anschluss.

## CAN-Terminierung

Das Board hat einen reservierten 120-Ohm-Widerstand fuer CAN, der laut Hersteller **standardmaessig nicht bestueckt bzw. nicht aktiviert** ist (NC) und per Jumper aktiviert werden kann.

Fuer die vorgesehene Stichleitung:

- Terminierung **deaktiviert** lassen.
- Die Jumperstellung vor dem Anschluss am Fahrzeug **am eigenen Board pruefen**. Der Herstellerstandard ist NC, aber das ist keine Garantie fuer das gelieferte Exemplar.
- Bei ausgeschalteter Terminierung darf ein Multimeter zwischen CAN H und CAN L im spannungsfreien Zustand **nicht** etwa 120 Ohm messen. Ein Messwert um 120 Ohm deutet auf eine aktive Terminierung hin.
- Terminierung nicht "zur Sicherheit" einschalten. Eine zusaetzliche Terminierung kann den Bus belasten und ist fuer eine Stichleitung falsch.
- Die Stichleitung kurz halten, verdrillt ausfuehren und nicht als Stern verteilen.

Die RS485-Terminierung ist fuer dieses Projekt irrelevant und bleibt ebenfalls unangetastet.

## OBD2-Pigtail und Fahrzeugzugang

Fuer den ersten Test wird ein OBD2-Pigtail verwendet:

- **Pin 6 = CAN-H**
- **Pin 14 = CAN-L**
- Pin 16 (+12 V) und Pin 4/5 (Masse) werden fuer diese passive Messung **nicht** benoetigt; das Board wird ueber USB-C versorgt.
- Keine anderen OBD2-Pins anschliessen. Keine Diagnoseanfragen senden.

**Gateway-Hinweis:** Der Volvo-Gateway kann den passiven Zugriff auf interne CAN-Nachrichten einschraenken. Der OBD2-Port liefert moeglicherweise nur einen Teil des Busses oder gefilterte Nachrichten. Das ist eine Fahrzeug-/Gateway-Eigenschaft, kein Fehler der Firmware. Die Einschraenkung wird dokumentiert und nicht durch aktive Anfragen umgangen.

Vor dem Anschluss: Fahrzeug steht, keine Fahrt, Terminierung deaktiviert, CAN H/L korrekt, Board ueber USB versorgt.

## Galvanische Isolation

CAN- und RS485-Schnittstelle sind laut Hersteller isoliert; das Board besitzt eine isolierte Spannungsversorgung fuer die Schnittstellenseite. Die Isolation nicht durch zusaetzliche Massebruecken oder ungeeignete Messgeraete ueberbruecken. Bei Unsicherheit den Schaltplan und ein isoliertes Messgeraet verwenden.

## Ausgaenge GPIO1/GPIO2

GPIO1 und GPIO2 sind 3,3-V-Logikpegel und im Beispiel nicht belegt. In V0.1 gilt:

- Beim Boot und bei Fehlern werden beide Pins **hochohmig (INPUT)** geschaltet und **nicht angesteuert**.
- Es wird bewusst **kein LOW** ausgegeben: Ein LOW-Pegel koennte ein LOW-aktives Relais einschalten. Ein HIGH-Pegel koennte ein HIGH-aktives Relais einschalten. Ohne definierte Treiberschaltung ist Hochohmigkeit die sicherste gemeinsame Variante.
- Die externe Beschaltung muss den inaktiven Zustand festlegen. Fuer ein LOW-aktives Relais ist typischerweise ein Pull-up auf der Treiberseite erforderlich; fuer HIGH-aktiv ein Pull-down. Das ist Teil der spaeteren Treiberschaltung, nicht der V0.1-Firmware.
- Es gibt keinen API-Endpunkt und keinen Taster, der sie einschalten kann.
- Auch ein versehentlicher Aufruf der internen Funktion bleibt durch die harte Sperre wirkungslos.
- **Keine Relais, LEDs, Ventile oder Leistungstreiber direkt anschliessen.** Ein spaeterer Ausbau braucht eine definierte Treiberstufe (Transistor/MOSFET, Freilaufdiode, Sicherung, passende Spannungsversorgung) und eine Sicherheitsbewertung.
- Die gewuenschten spaeteren Funktionen (Manövrierleuchten, Ambientebeleuchtung/Sternenhimmel) sind nur als Architektur vorbereitet, nicht als fertige Fahrzeugfunktion.

## Energie und Ruhezustand

- Versorgung ueber USB 5 V oder Klemme 7-36 V. Polaritaet und Spannungsbereich pruefen; im Fahrzeug eine geeignete Sicherung vorsehen.
- Der ESP32 kann im **Deep Sleep** das TWAI-Peripherie nicht weiter betreiben. Normale CAN-Frames koennen im Deep Sleep nicht empfangen oder ausgewertet werden.
- Ein Aufwecken per CAN ist mit der onboard vorhandenen Beschaltung nicht automatisch moeglich. Dafuer waere zusaetzliche Hardware noetig, z. B. ein CAN-Transceiver mit Wake-Funktion oder eine externe Komparator-/Monostabil-Schaltung, die ein geeignetes Wake-GPIO erzeugt. Die genaue Schaltung ist vor einer Umsetzung zu entwerfen und zu pruefen.
- CAN-Stille ist **kein** sicherer Beweis fuer Fahrzeug-Ruhe. Erst nach experimentell bestaetigten Signalen darf spaeter eine Schlafautomatik entstehen. In V0.1 gibt es keine automatische Deep-Sleep-Aktivierung.

## Board-Einstellungen in PlatformIO

Die Firmware verwendet:

- `board = esp32-s3-devkitc-1` als Basis
- 16 MB Flash (`board_build.flash_size`, `board_upload.flash_size`, `board_upload.maximum_size = 16777216`)
- OPI-PSRAM (`board_build.arduino.memory_type = qio_opi`)
- USB-CDC (`ARDUINO_USB_CDC_ON_BOOT=1`, `ARDUINO_USB_MODE=1`)
- eigene 16-MB-Partitionstabelle mit 4-MB-App-Partitionen

Die PlatformIO-Ausgabe kann das Board als "N8 (No PSRAM)" bezeichnen, weil die generische DevKitC-Boarddefinition verwendet wird. Die OPI-PSRAM-Bibliotheken werden trotzdem eingebunden. Am realen Board wurde der PSRAM am 04.11.2026 bestaetigt (8 MB gesamt, 16.384-Frame-Puffer im PSRAM). `tools/check_board_config.py` prueft die statischen Einstellungen.

## Weitere Hinweise

- Das Board besitzt eine RTC (PCF85063) und einen RTC-Batterieanschluss. In V0.1 werden Zeitstempel ausschliesslich monoton ueber `esp_timer_get_time()` seit dem Boot erzeugt, nicht als Wanduhrzeit.
- Die CAN-LED blinkt bei Busaktivitaet; sie ist kein Beweis fuer gueltige Frames oder die richtige Bitrate.
- Die RESET-Taste startet das Board neu; die BOOT-Taste wird fuer den Download-Modus benoetigt.
- Keine Firmware aus diesem Projekt auf ein fremdes Fahrzeug aufspielen. Nur autorisierte, eigene Diagnose.
