# Signalziele CEM-CAN

Alle Signale starten als **UNBEKANNT**. Es sind keine CAN-IDs, Bytes oder
Bitmasken fuer den CEM-CAN bestaetigt. Die Tabelle ist eine Suchliste, keine
Decoderdefinition.

## Manövrierleuchten

| Nr. | Signal | Anzeige | Status | Suchhinweis |
|---:|---|---|---|---|
| 1 | Rueckwaertsgang aktiv | virtuelle LED | UNBEKANNT | R einlegen, Gegenprobe N/D |
| 2 | Fahrgeschwindigkeit | numerisch km/h | UNBEKANNT | langsam rollen, mehrere Geschwindigkeiten |
| 3 | Abblendlicht aktiv | virtuelle LED | UNBEKANNT | AUS/Abblendlicht, 20-s-Phasen |
| 4 | Fernlicht aktiv | virtuelle LED | UNBEKANNT | AUS/Fernlicht, 20-s-Phasen |
| 5 | Parkkamera/Rangiermodus aktiv | virtuelle LED | UNBEKANNT | Kamera manuell, R, Gegenprobe |

## Ambientebeleuchtung

| Nr. | Signal | Anzeige | Status | Suchhinweis |
|---:|---|---|---|---|
| 6 | Fahrzeug entriegelt | virtuelle LED | UNBEKANNT | verriegeln/entriegeln |
| 7 | Fahrzeug von aussen verriegelt | virtuelle LED | UNBEKANNT | verriegeln/entriegeln |
| 8 | Fahrertuer geoeffnet | virtuelle LED | UNBEKANNT | Tuer auf/zu |
| 9 | Zuendungsstatus | virtuelle LED | UNBEKANNT | Zuendung EIN/AUS |
| 10 | Komfortbetrieb/Radio aktiv | virtuelle LED | UNBEKANNT | Radio/Komfort ein/aus |
| 11 | Fahrzeug wach | virtuelle LED | UNBEKANNT | Bus-Aktivitaet/Timeout |
| 12 | Fahrzeug im Ruhezustand | virtuelle LED | UNBEKANNT | Bus-Stille/Timeout |

## Testprotokoll

- Mindestens 4 EIN/AUS-Zyklen, 15-20 s stabile Phasen.
- Aktion sofort und exakt markieren, nicht erst am Phasenende.
- Gegenaktion und mindestens 3 unabhaengige Wiederholungen.
- Kontrollmessung ohne Bedienung.
- Zyklische Zaehler/Pruefsummen gesondert bewerten.
- Kandidat erst nach mehrfacher erfolgreicher Gegenprobe bestaetigen.
- Keine IDs oder Bitmasken erfinden.

## Sicherheit

Nur passiv empfangen. Kein Senden, keine Diagnoseanfragen, keine
Gateway-Manipulation, keine Steuergeraetecodierung. Hardwarefreigabe gemaess
`HARDWARE_CEM.md` abwarten.
