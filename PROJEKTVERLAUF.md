# Projektverlauf

## Fahrzeug

Ich untersuche einen Volvo V90 T8, Baujahr 2021, auf der SPA-Plattform. Die
Analyse läuft über zwei Wege: den OBD-Diagnosebus an Pin 6/14 und den internen
CEM-Bus hinter dem Fahrerfach.

## Ziel

Ich möchte die CAN-Nachrichten dieser beiden Busse passiv lesen und die
Zusammenhänge verstehen. Im Mittelpunkt stehen:

- Rückwärtsgang und Geschwindigkeit
- Abblendlicht, Fernlicht, Standlicht und Wegbeleuchtung
- Blinker links/rechts und Warnblinker
- Parkkamera und Rangiermodus
- Ver- und Entriegelung, Fahrertür
- Zündung, Komfort/Radio und Busruhe

Ich sende nichts auf den Bus, stelle keine Diagnoseanfragen und ändere keine
Steuergeräte. Das Projekt ist ausschließlich lesend.

## Hardware

- Waveshare ESP32-S3-RS485-CAN
- Isolierter Transceiver TJA1051 und Digitalisolator
- CAN TX auf GPIO15, RX auf GPIO16
- Echter TXD bleibt `INPUT_PULLUP`, TWAI-TX liegt auf Dummy-GPIO48
- 120-Ohm-Terminierung: Standard aus, am realen Board noch prüfen
- USB-CDC zum Laptop, WLAN-AP der Firmware optional

## Verlauf

### 04.11.2026: OBD-Low-Bus

Die ersten passiven Tests liefen am OBD2-Port. Ich habe einen USB-Logger,
eine lokale Weboberfläche und die CSV-Aufzeichnung aufgebaut. Als Kandidaten
sind mir damals aufgefallen:

- Fahrstufe P/R/N/D: `0x1FFF00A0`, Byte 6, Bits 0-1
- Fußbremse: `0x1FFF0200`, Byte 4, Bit 1
- Rückfahrkamera: `0x1FFF0144`, Byte 2, Bit 3, aktiv bei 0

Abblendlicht, Fernlicht, Standlicht, Parkbremse und die manuelle Kamera waren
auf diesem Bus nicht stabil zu sehen. Die drei Einträge sind Referenzen und
keine bestätigten CEM-Signale.

### 05.11.2026: CEM-Bus und Sicherheit

Beim Aufbau des CEM-Projekts habe ich den internen Bus analysiert. Ein früherer
automatischer Bitratenscan mit mehreren TWAI-Initialisierungen hat am Fahrzeug
Blinkleuchten und Beleuchtung gestört. Nach dem Trennen der USB-Versorgung war
wieder Ruhe.

Seitdem gilt: kein Scan, fester Testbetrieb mit 500 kbit/s, nur `LISTEN_ONLY`,
expliziter Start, kein Auto-Neuversuch und Dummy-TX. Die 500 kbit/s wurden
später mit echten Frames bestätigt. Im 500-kbit/s-Log waren 159.617 Frames und
24 Standard-IDs, ohne Demo- oder Parse-Fehler. 8.735 Frames in 10 Sekunden
passen zur Bitrate.

### 06.11.2026: Live-Tests und Auswertung

Am Abend habe ich mehrere live aufgezeichnete Tests gefahren, insgesamt
mehrere Millionen Frames. Der Empfang lief normal ohne Busfehler. Fehler
kamen erst auf, als der Bus während der Wegbeleuchtungs-Tests schlafen ging
und wieder aufwachte. CAN wurde dabei nie gesendet.

Für die Lichtzustände auf `0x030`/`0x035` habe ich folgende Werte gefunden:
`86 03` für Abblendlicht, `92 2B` für manuelles Fernlicht, `92 6B` für
Fernlicht in der Automatik/Nacht und `7C69` für die Lichthupe bei
ausgeschaltetem Abblendlicht. `7C60` scheint zur Wegbeleuchtung zu gehören,
der Einschaltbefehl fehlt aber noch.

Für die Blinker gilt: `0x040` Byte 5 Bit 4 ist links, Bit 5 ist rechts. Beim
Warnblinker sind beide Bits aktiv. Der normale Blinkstatus liegt in `0x050`
Byte 4-7 bei `01 90 01 90`; beim Warnblinker sind es `01 F4 01 2C`.

Bremspedal und Fahrstufe N/R konnte ich auf dem CEM-11-Bit-Bus nicht finden.
Die bekannten IDs dafür liegen auf dem OBD-Low-Bus.

## Aktueller Stand

| Bereich | Ergebnis |
|---|---|
| CEM-Bitrate | 500 kbit/s, mit echten Frames bestätigt |
| CEM-IDs | 24 Standard-IDs, keine Extended-IDs |
| CEM-Fehler | im normalen Empfang keine Busfehler |
| Licht | Abblendlicht und Fernlicht mehrfach bestätigt |
| Blinker | links, rechts und Warnblinker getrennt |
| Wegbeleuchtung | Zustand `7C60` sichtbar, Trigger noch offen |
| Bremse / Fahrstufe | auf diesem Bus nicht sichtbar |
| Hardware | Passivität noch nicht vollständig gemessen |

## Offene Punkte

1. Wo genau wird die Wegbeleuchtung eingeschaltet, und gibt es dafür einen
   Befehl auf dem Bus?
2. Kommen Bremspedal und Fahrstufe nur auf dem OBD-Low-Bus?
3. Stimmen die 500 kbit/s auch bei einer zweiten Gegenmessung?
4. Wie sind Board-Revision, Jumper und tatsächlicher TXD-Pfad?
5. Welche Zustände sollen als Nächstes dokumentiert werden?

Die Rohdaten bleiben lokal. Im Repository stehen nur die ausgewerteten
Ergebnisse und der Code.
