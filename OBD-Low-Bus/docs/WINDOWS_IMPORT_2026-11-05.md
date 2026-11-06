# Windows-CAN-Import vom 05.11.2026

Der neuere Windows-Stand des bisherigen CAN-Projekts wurde vollstaendig in
`OBD-Low-Bus/` uebernommen.

## Quelle

- Windows-Laptop: `%USERPROFILE%\Documents\Volvo-CAN-Control`
- Uebergabe/Staging auf dem Server: `../../_windows_import/`
  - `source.tar.gz` - Quellcode/Web/Tools/Tests/Docs ohne Caches und ohne Messungen
  - `messungen.tar.gz` - alle Windows-Messungen
  - `source/` - entpackter Quellstand
  - `legacy_root_20261105/` - alter Server-Rootstand vor der Umstrukturierung

## Importierte Messungen

- **183 Dateien, 833 MB** unter `../messungen/`
- Enthalten: Session-CSVs, Roh-JSONL, Event-/Meta-Logs, benannte Messungen
- Finales Abendarchiv: `../messungen/abend_20261104/alle_frames.csv`
  - **974.416 Frames** bis **2026-11-04T21:25:35.640+00:00**
  - Haupt-Abschaltzeit: **21:20:36.418**
  - Wake-up danach: **21:24:30.010 bis 21:25:35.640** (0x1FFF0148/014B)

## Importierter Softwarestand

- Firmware unter `../firmware/` (Waveshare ESP32-S3-RS485-CAN)
- Lokale Windows-Oberflaeche unter `../local_web/`
- Tools/Tests/Docs unter `../tools/`, `../tests/`, `../docs/`
- Laufzeit-Signale unter `../config/`, Referenzen unter `../decoder/`

## Abgrenzung

Die Windows-DoIP-/UDS-/DTC-Uebergabe vom 05.11.2026 ist **kein CAN-Stand**
und gehoert zum CEM-/Diagnosekontext:
`../../OBD-CEM-Bus/UEBERGABE_WINDOWS_DIAGNOSE_2026-11-05/`.

Die Diff-Datei des damaligen Windows-vs.-Server-Stands liegt unter
`WINDOWS_VS_SERVER_DIFF.md` im selben Docs-Ordner. Sie ist ein historischer
Snapshot, kein aktueller Soll-Ist-Vergleich.

## Secrets

`firmware/include/secrets.h` bleibt lokal und ist **nicht** Bestandteil der
Software-ZIPs. Die ZIPs enthalten nur `secrets.example.h`.
