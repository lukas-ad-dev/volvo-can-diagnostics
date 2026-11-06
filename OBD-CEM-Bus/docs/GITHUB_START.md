# GitHub in 10 Minuten – einfache Anleitung

Das lokale Git-Repository ist bereits vorbereitet und der erste Commit liegt
unter `%USERPROFILE%\Desktop\OBD-CEM-Bus`.

## Wichtig vorab

- **Privates Repository** verwenden. Das Projekt enthält Fahrzeugdaten,
  Diagnose-Ergebnisse und persönliche Konfiguration.
- **Nicht hochladen:** `firmware/include/secrets.h`, `.venv`, `.pio`,
  `messungen/`, `SAVE_*/` und Archive. Diese sind in `.gitignore` ausgeschlossen.
- GitHub ist nur der Online-Speicher. Deine Dateien bleiben lokal; GitHub
  speichert die Versionsstände.

## Variante A: GitHub Desktop (empfohlen, ohne Kommandozeile)

1. Konto erstellen: <https://github.com/signup>
   - E-Mail bestätigen, Benutzername und Passwort wählen.
2. GitHub Desktop installieren: <https://desktop.github.com/>
3. GitHub Desktop starten und mit dem GitHub-Konto anmelden.
4. **File → Add Local Repository**.
5. Ordner wählen: `%USERPROFILE%\Desktop\OBD-CEM-Bus`
6. GitHub Desktop erkennt das Repository. Oben auf **Publish repository**
   klicken.
7. Name z. B. `volvo-can-cem`, **Keep this code private** anhaken,
   **Publish repository**.
8. Fertig. Oben rechts steht der Repository-Link; den kannst du kopieren.

Spätere Änderungen:

1. GitHub Desktop öffnen.
2. Links unter **Changes** die Änderungen prüfen.
3. Unten eine kurze Beschreibung eintragen, **Commit to main**.
4. Oben **Push origin** klicken.

## Variante B: Kommandozeile

1. Auf <https://github.com/new> ein **leeres, privates** Repository anlegen:
   - Name: `volvo-can-cem`
   - **Private**
   - **Kein** README, **keine** .gitignore, **keine** Lizenz hinzufügen.
2. Die angezeigte HTTPS-URL kopieren, z. B.
   `https://github.com/DEINNAME/volvo-can-cem.git`
3. PowerShell im Projektordner öffnen:

```powershell
cd %USERPROFILE%\Desktop\OBD-CEM-Bus
git remote add origin https://github.com/DEINNAME/volvo-can-cem.git
git branch -M main
git push -u origin main
```

4. Beim Anmeldefenster:
   - GitHub-Benutzername eingeben.
   - Als Passwort **kein** normales GitHub-Passwort verwenden.
   - Entweder den Browser-Login von Git Credential Manager nutzen,
   - oder ein Personal Access Token erzeugen:
     GitHub → Settings → Developer settings → Personal access tokens →
     Tokens (classic) → Generate new token → Scope `repo` → Token als
     Passwort einfügen.

## Spätere Änderungen (Kommandozeile)

```powershell
cd %USERPROFILE%\Desktop\OBD-CEM-Bus
git status
git add .
git commit -m "Kurze Beschreibung der Änderung"
git push
```

## Wenn etwas nicht klappt

- **Authentication failed:** Personal Access Token statt Passwort verwenden.
- **Repository not found:** URL/Username prüfen; Repository muss existieren.
- **Large files:** nicht `SAVE_*`, `messungen`, `.pio` oder `.venv` hinzufügen.
- **Falsche Dateien committet:** `git status` prüfen; keine Secrets committen.

## Was aktuell im Repository ist

- Firmware-Quellcode (500 kbit/s, LISTEN_ONLY, Dummy-TX GPIO48)
- lokale Web-GUI und Diagnose-Tools
- Tests und Sicherheitschecks
- Konfiguration und Dokumentation
- Startknopf-Skripte

Nicht enthalten: Secrets, WLAN-Passwort, Binärdateien, Roh-Messdaten und
Archivdateien.
