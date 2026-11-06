# Messungen CEM-CAN

Es liegen noch **keine CEM-Messungen** vor.

## Referenz

Die vorhandenen OBD-Low-Bus-Messungen bleiben unveraendert unter:

`/projekte/Volvo/OBD-Low-Bus/messungen/`

Sie sind fuer den CEM-CAN nur Referenz. Insbesondere die dort gefundenen
IDs `0x1FFF00A0`, `0x1FFF0200` und `0x1FFF0144` sind **nicht** als
CEM-Decoder bestaetigt.

## Erster CEM-Test (nach Hardwarefreigabe)

1. Hardwarepruefung gemaess `SICHERHEIT_CAN_500.md` und `HARDWARE_CEM.md` abschliessen.
2. USB-C am Laptop, Boot-Status `STOP` pruefen; **keinen lokalen CAN-Server starten**.
3. Feste Bitrate 500 kbit/s, START nur explizit (Desktop-Knopf/Browser/API), nur LISTEN_ONLY; kein Bitratenscan.
4. Zunaechst 2-5 Minuten Rohdaten aufnehmen, danach erste A/B-Tests.
5. Alle Messungen unter `messungen/` dieses Projekts speichern.
6. Keine aktiven Anfragen, keine Gateway-Manipulation.

Der lokale Server schreibt alle Frames auf den Laptop; der ESP speichert
keine Frame-Logs.
