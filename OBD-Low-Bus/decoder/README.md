# Decoder OBD-Low-Bus

Dieser Ordner ist das Referenzarchiv der OBD-Low-Bus-Signaldefinitionen.
Die Laufzeit liest weiterhin `../config/signals.json`.

## Identifizierte Signale (Kandidaten, nicht formal bestaetigt)

| Signal | CAN-ID | Byte | Bit/Maske | Aktivwert | Status |
|---|---|---|---|---|---|
| Fahrstufe P | 0x1FFF00A0 | 6 | Maske 0x03 | 0x00 | Kandidat |
| Fahrstufe R | 0x1FFF00A0 | 6 | Maske 0x03 | 0x01 | Kandidat |
| Fahrstufe N | 0x1FFF00A0 | 6 | Maske 0x03 | 0x02 | Kandidat |
| Fahrstufe D | 0x1FFF00A0 | 6 | Maske 0x03 | 0x03 | Kandidat |
| Fussbremse | 0x1FFF0200 | 4 | Bit 1 / 0x02 | 0x02 | Kandidat |
| Rueckfahrkamera/Rueckansicht | 0x1FFF0144 | 2 | Bit 3 / 0x08 | 0x00 | Kandidat |

Weitere Signale (Abblendlicht, Fernlicht, Standlicht, Parkkamera 360,
Parkbremse, Tueren, Verriegelung, Zuendung, Komfort/Radio) sind auf dem
beobachteten OBD-Diagnosebus **nicht** als stabile Bits identifiziert.

Die Messdateien und der Abend-Archivstand liegen unter `../messungen/`.
Die Definitionen in `signals.json` sind Laufzeit-Kandidaten; bitte keine
IDs erfinden oder als bestaetigt markieren, solange die Gegenprobe fehlt.
