# Messungen 04.11.2026 - OBD-Low-Bus

Die Messdateien liegen lokal im Projektordner. Hier stehen die wichtigsten
Ergebnisse und Dateinamen als Dokumentation.

## Wichtige Messdateien

- `20261104-202833_rueckwaertsgang_live_1.csv` - R-Live-Test
- `20261104-202913_rueckwaertsgang_live_2_gegenlauf.csv` - R-Gegenlauf
- `20261104-203059_rueckwaertsgang_muster_1.csv` - N/R-Muster
- `20261104-203859_abblendlicht_muster_1.csv` - Abblendlicht
- `20261104-204421_licht_aus_abblendlicht_20s.csv` - AUS/Abblendlicht
- `20261104-204933_fernlicht_aus_an_20s.csv` - AUS/Fernlicht
- `20261104-205343_gang_n_d_10s.csv` - N/D
- `20261104-210228_parkbremse_geloest_fest_20s.csv` - Parkbremse erster Test
- `20261104-210932_fussbremse_isoliert_15s.csv` - Fussbremse isoliert
- `20261104-211148_parkbremse_isoliert_bit0.csv` - Parkbremse isoliert
- `20261104-215343_kamera_p_r_test_1.csv` - Kamera P/R
- `20261104-220154_freies_ausprobieren_1.csv` - freie Body-Aktionen
- `20261104-221946_auto_aus_aussteigen_1.csv` - Auto aus/Aussteigen

## Wichtigste Ergebnisse

- Fahrstufen P/R/N/D: `0x1FFF00A0`, Byte 6, Bits 0-1.
- Fussbremse: `0x1FFF0200`, Byte 4, Bit 1.
- Rueckfahrkamera/Rueckansicht: `0x1FFF0144`, Byte 2, Bit 3, aktiv bei 0.
- Abblendlicht, Fernlicht, Standlicht, Parkbremse und manuelle 360-Kamera:
  kein stabiler Kandidat auf dem OBD-Diagnosebus.
- Body-Aktionen (Tueren, Fenster, Spiegel, Sitz, Lenkradtasten, Kofferraum)
  erzeugten keine neuen IDs/Bits.
- Auto-Aus: gleichzeitiger Stopp fast aller IDs um 21:20:36.418; letzter
  Diagnoseframe um 21:22:50.780. Ein eigenes Zuendungs-aus-Bit wurde nicht
  bestaetigt; der Frame-Timeout ist der zuverlaessige Indikator.

## Logging-Stand

Der lokale Server wurde am 04.11.2026 auf getrennten Serial-Reader/Processor
und groesseren USB-Puffer umgestellt. Im 35-s-Test: 0 verworfene Frames,
0 Parse-Fehler. Die Messdateien sind auf dem Laptop und im Abendarchiv gesichert.


## Nachtrag finales Archiv

- Das finale `abend_20261104/alle_frames.csv` enthaelt **974.416 Frames**
  bis **2026-11-04T21:25:35.640+00:00**.
- Nach dem Auto-Aus folgte ein Wake-up von **21:24:30.010** bis
  **21:25:35.640** (nur `0x1FFF0148` und `0x1FFF014B`).
- Der letzte Frame der eigentlichen Auto-Aus-Messung war 21:22:50.780;
  der finale Sessionframe ist 21:25:35.640.
