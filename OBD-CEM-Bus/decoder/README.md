# Decoder-Referenz CEM

**Alle Fahrzeugdecoder in diesem Ordner sind UNVERIFIZIERT AUF CEM.**

Die Dateien wurden aus dem OBD-Low-Bus-Projekt uebernommen, um spaeter
vergleichen zu koennen. Auf dem CEM-CAN wurde noch keine dieser IDs,
Bytereihenfolgen oder Bitmasken nachgewiesen. Es duerfen keine IDs erfunden
oder als bestaetigt markiert werden.

## Referenz aus OBD-Low-Bus (nicht auf CEM bestaetigt)

| Signal | CAN-ID | Byte | Bit/Maske | Aktivwert |
|---|---|---|---|---|
| Fahrstufe P | 0x1FFF00A0 | 6 | Maske 0x03 | 0x00 |
| Fahrstufe R | 0x1FFF00A0 | 6 | Maske 0x03 | 0x01 |
| Fahrstufe N | 0x1FFF00A0 | 6 | Maske 0x03 | 0x02 |
| Fahrstufe D | 0x1FFF00A0 | 6 | Maske 0x03 | 0x03 |
| Fussbremse | 0x1FFF0200 | 4 | Bit 1 / 0x02 | 0x02 |
| Rueckfahrkamera/Rueckansicht | 0x1FFF0144 | 2 | Bit 3 / 0x08 | 0x00 |

Diese IDs gelten ausschliesslich als Suchhypothesen fuer den CEM-CAN.
Ein Decoder wird erst nach mehreren praktischen Gegenproben auf dem CEM-CAN
bestaetigt. `config/signals.json` fuehrt sie deshalb mit Status `unknown`.
