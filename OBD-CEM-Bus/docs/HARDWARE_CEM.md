# Hardware: CEM-CAN im Volvo V90 T8 (SPA, MJ 2021)

## Ziel

Passiver Abgriff des internen CAN-Busses am CEM (Central Electronic Module)
eines Volvo V90 T8, Modelljahr 2021, SPA-Plattform. Es wird ausschliesslich
empfangen. Es werden keine CAN-Nachrichten gesendet, keine Diagnoseanfragen
gestellt und keine Gateway-Funktionen manipuliert.

## Referenz auf die Einbauanleitung

Es gibt eine Einbauanleitung des CANM8-/CANNECT-Interfaces fuer den Volvo V90:

- <https://www.transportstyling.se/produktfiler/volvov902016-.pdf>

Dort wird ein CAN-Abgriff hinter dem kleinen Fahrerfach links unterhalb des
Lenkrads beschrieben. Die Anleitung bezieht sich auf eine andere
Modellausfuehrung und ist fuer den konkreten V90 T8 von 2021 **nicht
verifiziert**. Sie ist nur eine Orientierung, keine Freigabe zum Anschliessen.

## Vorlaeufige Kabelfarben (NICHT bestaetigt)

In der genannten Anleitung werden fuer die dort beschriebene Ausfuehrung
genannt:

- **CAN-High:** Grau/Braun
- **CAN-Low:** Gelb/Lila

Diese Angaben sind **vorlaeufig**. Kabelfarben koennen sich zwischen
Ausstattungsvarianten, Modelljahren und Produktionsstaenden aendern.
Vor dem Anschluss zwingend pruefen:

1. Fahrzeug-Werkstattdokumentation / Schaltplan fuer die konkrete FIN.
2. Durchgangsmessung und Leitungsverfolgung mit einem Multimeter.
3. Keine Zuordnung ausschliesslich nach Farbe.

## Physikalischer CAN-Standard - zwingend vor Anschluss klaeren

Der Waveshare Industrial ESP32-S3-RS485-CAN besitzt einen **High-Speed-CAN-
Transceiver TJA1051** (ISO 11898-2). Der physikalische Standard des
CEM-Busses muss vor dem Anschluss eindeutig bestimmt werden:

- **High-Speed CAN (ISO 11898-2):** kompatibel zum TJA1051, Differenzbus,
  typische Bitraten 125/250/500 kbit/s. Die Firmware laeuft aktuell fest mit
  **500 kbit/s**, Boot = `STOP`, `START` per Compile-Flag gesperrt.
- **Low-Speed Fault-Tolerant CAN (ISO 11898-3):** **nicht** ohne weiteres
  kompatibel. Andere Pegel, Fehlertoleranz und Terminierung. Der TJA1051
  darf nicht blind an einen solchen Bus angeschlossen werden.
- **Nicht verbinden**, solange der Standard nicht durch Schaltplan,
  Messung oder Herstellerdokumentation bestaetigt ist.

**Keine Fahrzeug-CAN-Netze miteinander verbinden.** Kein OBD-Gateway
ueberbruecken, keine aktive Diagnosesitzung, keine Gateway-Umgehung.

### Transceiver-Ruhezustand (Schaltplan)

- Der TJA1051T/3/1J (U8) hat am TXD-Pin einen internen Pull-up; HIGH bedeutet
  rezessiv. Der S-Pin liegt ueber R18 0R auf SGND, also **Normal Mode ohne
  Silent-/Standby-Steuerung**.
- Der Digitalisolator π163E31 (U9, E31 = Fail-Safe HIGH) treibt TXD2' bei
  offenem Eingang HIGH. Die NC-Widerstaende R35-R39 sind laut Schaltplan nicht
  bestueckt; offene Eingaenge sind damit sicher HIGH.
- Die Firmware haelt den echten CAN-TXD **GPIO15 dauerhaft auf
  `INPUT_PULLUP`**. TWAI-TX wird auf den ungenutzten **Dummy-GPIO48** gelegt;
  damit kann der ESP32 den Transceiver auch bei einem TWAI-Init-Glitch nicht
  dominant treiben. GPIO48 muss am internen Header unbeschaltet bleiben.
- Boot/STOP: GPIO15 hoch, U9-Ausgang hoch, TJA1051-TXD hoch = rezessiv.
- START (erst nach Freigabe): TWAI-TX auf GPIO48, RX auf GPIO16; GPIO15 bleibt
  hoch. Vor dem Fahrzeuganschluss mit Oszilloskop verifizieren, dass waehrend
  des TWAI-Installs kein dominanter Impuls auf CAN-H/L entsteht.

## Terminierung und Leitung

- Die 120-Ohm-Terminierung des Waveshare-Boards ist standardmaessig **NC**
  und muss fuer die Stichleitung **deaktiviert** bleiben. Jumper am realen
  Board pruefen.
- Der Fahrzeugbus ist bereits terminiert. Keine zusaetzliche Terminierung
  einschalten.
- Stichleitung kurz, verdrillt und mit sauberer Zugentlastung ausfuehren.
- Keine Sternverteilung, keine offenen Stichreste, keine parallelen
  Experimente an mehreren CAN-Netzen.

## Stromversorgung

- Erster Test ausschliesslich ueber **USB-C** (5 V), keine 12-V-Klemme,
  keine Relais.
- Spaetere Fahrzeugversorgung nur mit Sicherung, gepruefter Polaritaet und
  geeignetem Schutzgehaeuse. Die CAN-Schnittstelle des Boards ist galvanisch
  isoliert; keine zusaetzliche Massebruecke ueber die Isolation legen.

## Pruef- und Anschlussablauf (Vorschlag, noch nicht freigegeben)

1. Fahrzeug steht, Zuendung aus, Schluessel ausserhalb der Reichweite.
2. Einbauort gemaess Anleitung lokalisieren, aber **noch nicht anschliessen**.
3. Schaltplan/FIN-Dokumentation und Kabelfarben pruefen.
4. Mit Multimeter Spannungs- und Widerstandswerte erfassen; CAN-H/CAN-L
   identifizieren. Bei Low-Speed-Fault-Tolerant-Verdacht abbrechen.
5. Board-Terminierung pruefen (aus).
6. Erst nach eindeutiger Bestaetigung des High-Speed-Standards CAN-H/CAN-L
   am CEM-Abgriff anschliessen. Keine anderen Pins, keine 12-V-Versorgung.
7. USB-C an den Laptop, Boot-Status `STOP` pruefen; feste Bitrate 500 kbit/s,
   `START` bleibt bis zur Hardwarefreigabe gesperrt. Kein Bitratenscan.
8. Keine aktiven Anfragen, keine Diagnosesitzung, keine Gateway-Manipulation.
9. Bei fehlenden oder fehlerhaften Frames: sofort `STOP`, nicht blind
   weiterprobieren; Verkabelung, Standard, Terminierung und TXD-Ruhepegel pruefen.
10. Fahrzeuganschluss erst nach vollstaendiger Hardwarepruefung und Freigabe
    gemaess `SICHERHEIT_CAN_500.md`.

## Offene Punkte

- Genaue CEM-Pinbelegung und Stecker fuer V90 T8 2021.
- Tatsaechlicher physikalischer Standard des CEM-Busses.
- Tatsaechliche Bitrate.
- Terminierung und Leitungslauf im Fahrzeug.
- Ob der CEM-Bus ueberhaupt passiv zugaenglich ist oder ebenfalls gateway-
  gefiltert wird.

Bei Unsicherheit eine qualifizierte Kfz-Elektrik-Fachkraft hinzuziehen.
Keine Empfehlung zum Anschluss an einen ungeprueften Bus.
