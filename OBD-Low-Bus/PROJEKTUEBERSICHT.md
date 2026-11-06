# Projektuebersicht - Volvo CAN Control

Stand: 2026-11-05

Dieses Verzeichnis enthaelt zwei getrennte, eigenstaendig ausfuehrbare
CAN-Diagnoseprojekte fuer einen Volvo V90 T8 (SPA, Modelljahr 2021) mit dem
Waveshare Industrial ESP32-S3-RS485-CAN.

## 1. Welcher Ordner behandelt welchen CAN-Bus?

| Ordner | Bus / Zweck | Status |
|---|---|---|
| `OBD-Low-Bus/` | bisheriger OBD-Diagnosebus (OBD2 Pin 6/14), USB-C-Liveanalyse, lokale Windows-Oberflaeche | funktionsfaehig, Messungen und Kandidaten vorhanden |
| `OBD-CEM-Bus/` | interner CEM-CAN hinter dem Fahrerfach, Vorbereitung fuer passiven Abgriff | Software baubar/getestet, keine CEM-Messungen, keine CEM-Decoder bestaetigt |

Der Name `OBD-Low-Bus` ist organisatorisch. Der tatsaechliche Bustyp und die
Bitrate sind nicht abschliessend bestaetigt.

## 2. Bisher identifizierte / bestaetigte CAN-Signale

### OBD-Low-Bus

Diese Signale wurden am 04.11.2026 praktisch geprueft. Sie sind im Projekt
weiterhin als **Kandidaten** gefuehrt, nicht formal mit drei unabhaengigen
Gegenproben bestaetigt:

| Signal | CAN-ID | Byte | Bit/Maske | Aktivwert |
|---|---|---|---|---|
| Fahrstufe P | 0x1FFF00A0 | 6 | Maske 0x03 | 0x00 |
| Fahrstufe R | 0x1FFF00A0 | 6 | Maske 0x03 | 0x01 |
| Fahrstufe N | 0x1FFF00A0 | 6 | Maske 0x03 | 0x02 |
| Fahrstufe D | 0x1FFF00A0 | 6 | Maske 0x03 | 0x03 |
| Fussbremse | 0x1FFF0200 | 4 | Bit 1 / 0x02 | 0x02 |
| Rueckfahrkamera/Rueckansicht | 0x1FFF0144 | 2 | Bit 3 / 0x08 | 0x00 |

**Nicht** auf dem OBD-Diagnosebus als stabile Signale identifiziert:
Abblendlicht, Fernlicht, Standlicht, Parkbremse, manuelle 360-Grad-Kamera,
Tueren/Verriegelung, Fenster, Spiegel, Sitz, Lenkradtasten, Kofferraum.

### OBD-CEM-Bus

- Keine Fahrzeugdecoder bestaetigt.
- Die Low-Bus-Decoder sind als **UNVERIFIZIERT AUF CEM** kopiert.
- Alle Fahrzeugziele stehen auf `UNBEKANNT`.

## 3. Noch gesuchte Signale im CEM-Projekt

Manövrierleuchten:
1. Rueckwaertsgang aktiv
2. Fahrgeschwindigkeit km/h
3. Abblendlicht aktiv
4. Fernlicht aktiv
5. Parkkamera/Rangiermodus aktiv

Ambientebeleuchtung:
6. Fahrzeug entriegelt
7. Fahrzeug von aussen verriegelt
8. Fahrertuer geoeffnet
9. Zuendungsstatus
10. Komfortbetrieb/Radio aktiv
11. Fahrzeug wach
12. Fahrzeug im Ruhezustand

## 4. Erforderliche Hardware

### OBD-Low-Bus

- Waveshare Industrial ESP32-S3-RS485-CAN
- USB-C-Datenkabel
- OBD2-Pigtail: Pin 6 = CAN-H, Pin 14 = CAN-L; keine 12-V-Versorgung
- Board-Terminierung aus, kurze verdrillte Stichleitung
- Windows-Laptop mit WLAN (fuer OpenCode/Internet) und USB

### OBD-CEM-Bus

- Dieselbe Waveshare-Hardware
- Zugang hinter dem kleinen Fahrerfach links unter dem Lenkrad
- Vorlaeufige Kabelfarben aus der CANM8-/CANNECT-Anleitung:
  CAN-H Grau/Braun, CAN-L Gelb/Lila - **nicht bestaetigt**
- **Vor Anschluss zwingend klaeren:** High-Speed CAN (ISO 11898-2) oder
  Low-Speed Fault-Tolerant CAN (ISO 11898-3). Der TJA1051 ist High-Speed;
  kein Anschluss an einen ungeprueften Low-Speed-Bus.
- Keine CAN-Netze miteinander verbinden, keine Gateway-Manipulation.
- Details: `OBD-CEM-Bus/docs/HARDWARE_CEM.md`

## 5. Uebertragung auf Windows

Die ZIP-Archive liegen im Volvo-Projektordner auf dem MGMT-Server:

- `OBD-Low-Bus.zip`
- `OBD-CEM-Bus.zip`

Download z. B. per SCP:

```powershell
scp user@SERVER:/projekte/Volvo/OBD-Low-Bus.zip .
scp user@SERVER:/projekte/Volvo/OBD-CEM-Bus.zip .
```

Dann entpacken und im jeweiligen Projektordner `start_obd_low.bat`
beziehungsweise `start_obd_cem.bat` starten. Die ZIPs enthalten keine
Messdateien, keine Build-Caches, keine `.venv` und keine `secrets.h`.
`firmware/include/secrets.example.h` nach `secrets.h` kopieren und das
WLAN-Passwort eintragen.

## 6. Zwischen OBD- und CEM-Profil wechseln

- Immer nur ein Profil gleichzeitig starten.
- Beide nutzen Port `127.0.0.1:8765` und denselben COM-Port.
- Der Starter prueft das laufende Profil. Wenn das andere Profil laeuft,
  verweigert er den Start mit einer klaren Meldung.
- Die lokale Oberflaeche zeigt das aktive Profil (`OBD-Low-Bus` oder
  `OBD-CEM-Bus`).
- Ein ESP32 kann nicht beide CAN-Netze gleichzeitig ueber denselben
  physischen CAN-Kanal lesen.

## 7. Durchgefuehrte Tests (MGMT-Core, 2026-11-05)

| Test | OBD-Low-Bus | OBD-CEM-Bus |
|---|---|---|
| PlatformIO-Firmware-Build `esp32s3` | SUCCESS | SUCCESS |
| Native C++-Tests | 9/9 | 9/9 |
| Python-Tests | 30/30 | 30/30 |
| Sicherheits-/Pin-/Board-Checks | OK | OK |
| Web-UI-Checks | OK | OK |
| Demo-Modus + Profilanzeige | OK (20 Signale) | OK (22 Signale) |
| CSV-/JSON-Export | OK | OK |
| Decoder-Ladefunktion | OK | OK (Referenzen unknown) |
| Profil-Sperre (Port 8765) | OK | OK |
| Hardware-Flash / Fahrzeug | **nicht durchgefuehrt** | **nicht durchgefuehrt** |

Die Windows-Hardwaretests vom 04.11.2026 (COM8, Flash, USB-CDC, Boot,
Demo, Messungen) sind im Low-Testbericht dokumentiert. Auf dem Server wurde
bewusst keine Hardware geflasht und kein Fahrzeug angeschlossen.

## 8. Offene Probleme

- Formale Drei-Lauf-Bestaetigung der Low-Bus-Kandidaten steht noch aus.
- Body-, Licht- und EPB-Signale sind auf dem OBD-Diagnosebus nicht sichtbar;
  dafuer ist ein Body-CAN-Zugang erforderlich.
- CEM-Bus: physischer Standard, Pinbelegung, Kabelfarben, Terminierung und
  Bitrate sind ungeklaert; keine CEM-Messungen.
- CEM-Decoder sind ausschliesslich unverifizierte Referenzen.
- Manuelle 360-Grad-Kamera und Parkbremse sind auf dem OBD-Bus nicht
  identifiziert.
- Ein ESP32 kann nicht beide Busse gleichzeitig lesen; das Profil muss
  bewusst gewaehlt werden.

## 9. Sicherung und Messdaten

- Vollstaendiges Server-Backup vor der Umstrukturierung:
  `backups/Volvo_backup_20261105-1712.tar.gz` (SHA256 im gleichen Ordner).
- Windows-Importstand: `_windows_import/`.
- Alle OBD-Low-Bus-Messungen:
  `OBD-Low-Bus/messungen/` inkl. `abend_20261104/alle_frames.csv`.
- CEM-Messungen: noch keine; `OBD-CEM-Bus/messungen/README.md`.
- Windows-DoIP-/DTC-Uebergabe vom 05.11.2026:
  `OBD-CEM-Bus/UEBERGABE_WINDOWS_DIAGNOSE_2026-11-05/` (DoIP/UDS, keine
  CAN-IDs; nicht im Software-ZIP; enthaelt VIN, nicht veroeffentlichen).
- Finales OBD-Low-Bus-Abendarchiv: **974.416 Frames** bis
  **2026-11-04T21:25:35.640+00:00** in
  `OBD-Low-Bus/messungen/abend_20261104/alle_frames.csv`.
