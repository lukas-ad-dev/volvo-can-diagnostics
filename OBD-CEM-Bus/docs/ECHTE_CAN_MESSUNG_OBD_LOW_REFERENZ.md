# Erste echte CAN-Messung am Volvo V90 T8 (SPA, MJ 2021)

> **STOPP (2026-11-05):** Dieser Leitfaden beschreibt einen frueheren Testaufbau.
> Aktuell gilt: **kein Fahrzeuganschluss, kein Bitratenscan und kein Serverstart**
> ohne Freigabe gemaess `docs/SICHERHEIT_CAN_500.md`. Die Firmware laeuft fest mit
> 500 kbit/s, Boot = `STOP`, `START` ist per Compile-Flag gesperrt.

Diese Anleitung beschreibt den passiven Anschluss des Waveshare ESP32-S3-RS485-CAN an den OBD2-Port. Sie ist erst nach erfolgreichem USB-Test und manueller Pruefung der Verdrahtung auszufuehren.

> **Sicherheit:** Das Fahrzeug steht, ist nicht in Bewegung und keine sicherheitsrelevante Aktion wird ausgeloest. Es wird ausschliesslich passiv empfangen. Die Firmware sendet keine CAN-Nachrichten, keine Diagnoseanfragen und keine UDS-/OBD-Anfragen. Keine Gateway-Umgehung, keine aktiven Diagnosesitzungen, keine Fremdfahrzeuge.

## 1. Benoetigte Teile

- Waveshare ESP32-S3-RS485-CAN, ueber USB-C mit dem Laptop verbunden.
- OBD2-Pigtail oder OBD2-Stecker mit zwei Litzen.
- Multimeter fuer Durchgang, Spannung und Widerstand.
- Optional: verdrillte, kurze CAN-Leitung und geeignete Aderendhuelsen.
- Keine 12-V-Versorgung, keine Relais, keine Leistungstreiber.

## 2. OBD2-Belegung

| OBD2-Pin | Signal | Verwendung |
| --- | --- | --- |
| 6 | CAN-H | an Klemme **H** des Waveshare |
| 14 | CAN-L | an Klemme **L** des Waveshare |
| 16 | +12 V | **nicht anschliessen** (Board wird ueber USB versorgt) |
| 4 / 5 | Masse | **nicht anschliessen** (keine Massebruecke ueber USB) |

Nur Pin 6 und Pin 14 verwenden. Andere Pins nicht belegen.

## 3. Vor dem Anschluss pruefen

1. **Fahrzeug steht**, Getriebe in P, Zuendung aus, Schluessel ausserhalb der Reichweite. Nicht waehrend der Fahrt anschliessen.
2. **Board-Pinbelegung:** Die Firmware nutzt die am 04.11.2026 verifizierte Belegung **CAN TX = GPIO15, CAN RX = GPIO16**. Der offizielle Waveshare-Schaltplan und `WS_GPIO.h` bestaetigen diese Zuordnung. Am realen Board trotzdem Silkscreen/Durchgang pruefen. Bei Abweichung nicht anschliessen.
3. **CAN-Terminierung:** Der 120-Ohm-Jumper auf dem Board muss **deaktiviert** bleiben (Herstellerstandard NC). Im spannungsfreien Zustand zwischen CAN-H und CAN-L am Board **nicht** ca. 120 Ohm messen. Die Fahrzeugseite ist bereits terminiert; eine zusaetzliche Stichleitungs-Terminierung ist falsch.
4. **Aderfarben mit dem Multimeter pruefen.** Nicht nach Farbe allein anschliessen. CAN-H und CAN-L nicht vertauschen.
5. **Kurzschlusspruefung:** Kein Kurzschluss zwischen H/L, H/GND, L/GND. Keine Spannung auf H/L, solange das Board nicht angeschlossen ist.
6. **Board ausschliesslich ueber USB-C versorgt.** Keine 12-V-Klemme, keine Fahrzeugspannung anloeten.

## 4. Anschliessen

1. USB-C-Datenkabel vom Laptop zum Waveshare stecken. Der Laptop bleibt mit seinem normalen WLAN/Internet verbunden; die ESP-Verbindung laeuft ueber USB-CDC.
2. OBD2-Pigtail am Fahrzeug einstecken, aber noch nicht mit dem Board verbinden.
3. Mit dem Multimeter am Pigtail pruefen: Pin 6 und Pin 14 sind die erwarteten CAN-Leitungen; keine unerwartete Spannung, kein Kurzschluss.
4. Pigtail CAN-H an Klemme **H**, CAN-L an Klemme **L** anschliessen. Zugentlastung, keine losen Draehte, keine Beruehrung benachbarter Pins.
5. Die Stichleitung kurz und verdrillt halten. Keine Sternverteilung, keine offenen Stichreste.

## 5. Erste Messung starten

1. Auf dem Desktop **Volvo CAN Control** oeffnen. Der Starter erkennt COM8/den ESP-Port, startet den lokalen Server und oeffnet `http://127.0.0.1:8765`.
2. Im Kopf der Oberflaeche muss **USB verbunden** und **Quelle USB-CDC** stehen. Der DEMO-Hinweis muss **aus** sein.
3. Fahrzeug in Zuendung/Komfortstellung bringen (ohne Motorstart, wenn moeglich). Der CAN-Bus kann je nach Gateway erst mit Fahrzeugaktivitaet Nachrichten liefern.
4. Im Reiter **Live-CAN-Monitor** Nachrichten beobachten:
   - CAN-ID, Datenbytes, DLC, STD/EXT, Nachrichten/s und Filter.
   - Fehler-/Verlustzaehler im Kopf und unter **Export & Status**.
5. Fuer eine Aufzeichnung **Aufzeichnung starten**, die Fahrzeugaktion ausfuehren, danach **Aufzeichnung stoppen**. Die CSV liegt unter `messungen\` und ist ueber **Messdateien** exportierbar.
6. Fuer die Signalerkennung den **Assistenten** verwenden: Grundzustand aufnehmen, Fahrzeugaktion markieren, Aktionsphase aufnehmen, auswerten. Kandidaten werden nur vorgeschlagen und bleiben **UNBEKANNT/KANDIDAT**, bis sie mehrfach mit Gegenaktion geprueft und dokumentiert bestaetigt wurden.

## 6. Bitrate

Die Firmware ist auf einen **festen Testbetrieb mit 500 kbit/s** beschraenkt. Es gibt
keinen automatischen Scan und keinen Wechsel auf 125/250 kbit/s. CAN bleibt beim
Boot deaktiviert; `START` ist bis zur Hardwarefreigabe per Compile-Flag gesperrt.
Vor jedem Fahrzeuganschluss die Hardwarepruefungen aus
`docs/SICHERHEIT_CAN_500.md` dokumentiert abschliessen. Keine aktiven
Diagnoseanfragen senden.

## 7. Wenn keine passiv lesbaren Nachrichten kommen

Der V90 MJ 2021 nutzt die SPA-Plattform mit einem zentralen Gateway. Der OBD2-Port kann nur einen gefilterten Teil des Busses oder erst nach einer Gateway-Freigabe Daten liefern. Das ist eine **Fahrzeug-/Gateway-Eigenschaft**, kein Firmwarefehler.

Anzeige in der Oberflaeche: **Keine CAN-Frames. Moegliche Ursachen: Gateway/Anschlussstelle, Bitrate, CAN H/L, Terminierung.**

Dann der Reihe nach pruefen:

1. USB-Verbindung und COM-Port.
2. CAN-H/CAN-L nicht vertauscht, feste Verbindung.
3. Board-Terminierung aus, Fahrzeugbus nicht durch zusaetzliche Terminierung belastet.
4. Feste Testbitrate 500 kbit/s (kein Scan, kein Wechsel); `START` bleibt bis zur Hardwarefreigabe gesperrt.
5. Fahrzeugzustand (Zuendung/Komfort), Gateway-Freigabe.
6. Keine aktiven Diagnoseanfragen, keine Umgehung des Gateways. Ein Gateway-Filter wird dokumentiert und **nicht** umgangen.

## 8. Nach der Messung

1. Aufzeichnung stoppen und CSV/JSON exportieren.
2. Zuendung aus, OBD2-Pigtail abziehen, USB trennen.
3. Board nicht am Fahrzeug lassen, solange keine geeignete, gesicherte Dauerstromversorgung und ein abgestimmtes Gehaeuse-/Kabelkonzept vorhanden sind.
4. Messdateien und Ereignisprotokolle sichern; keine WLAN-Zugangsdaten oder andere Secrets in Berichte uebernehmen.

## 9. Verbotene Schritte

- Kein CAN-Senden, kein Replay, keine UDS-/OBD-Anfragen.
- Keine Diagnosesitzung, keine Gateway-Umgehung, keine Manipulation.
- Keine Relais, keine GPIO1/GPIO2-Beschaltung ohne verifizierte Treiberstufe.
- Keine 12-V-Versorgung ohne Sicherung und gepruefte Polaritaet.
- Kein Anschluss an fremde Fahrzeuge.
