#!/usr/bin/env python3
"""Desktop-Starter fuer Volvo CAN Control.

Erkennt den ESP32-COM-Port, startet den lokalen Diagnoseserver auf
127.0.0.1:8765 und oeffnet die Weboberflaeche im Standardbrowser.
Ohne angeschlossenen ESP startet der Server trotzdem; die Oberflaeche
zeigt dann den Verbindungsfehler und sucht weiter nach dem Port.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

SERVICE = "volvo-can-diagnostics"


def probe(port: int):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.0) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read().decode("utf-8"))
            return payload if payload.get("service") == SERVICE else None
    except Exception:
        return None


def open_browser_when_ready(port: int) -> None:
    url = f"http://127.0.0.1:{port}/"
    for _ in range(80):
        if probe(port):
            webbrowser.open(url)
            return
        time.sleep(0.25)
    print(f"Weboberflaeche nicht erreichbar: {url}")


def find_port() -> str | None:
    try:
        from usb_can_logger import find_esp_port
    except ImportError as exc:
        print(f"Fehler: pyserial fehlt ({exc}).")
        print("Installation: python -m pip install -r tools\\requirements.txt")
        return None
    return find_esp_port()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Volvo CAN Control starten")
    parser.add_argument("--port", type=int, default=8765, help="HTTP-Port (Standard 8765)")
    parser.add_argument("--serial-port", default=None, help="COM-Port erzwingen, z. B. COM8")
    parser.add_argument("--demo", action="store_true", help="DEMO-Modus ohne USB-Hardware")
    parser.add_argument("--profile", default="OBD-CEM-Bus", help="Projektprofil (OBD-Low-Bus oder OBD-CEM-Bus)")
    parser.add_argument("--no-browser", action="store_true", help="Browser nicht automatisch oeffnen")
    args = parser.parse_args(argv)

    health = probe(args.port)
    if health:
        url = f"http://127.0.0.1:{args.port}/"
        running_profile = health.get("profile", "unbekannt")
        if running_profile != args.profile:
            print(f"Es laeuft bereits das Profil {running_profile!r} auf Port {args.port}.")
            print("Bitte dieses Serverfenster schliessen; es kann nur ein Profil den COM-Port nutzen.")
            return 1
        print(f"Volvo CAN Control ({running_profile}) laeuft bereits: {url}")
        if not args.no_browser:
            webbrowser.open(url)
        return 0

    explicit_port = args.serial_port
    if args.demo:
        print("DEMO-Modus: synthetische Frames, keine USB-Hardware.")
    else:
        detected = explicit_port or find_port()
        if detected:
            print(f"ESP32 erkannt: {detected}")
        else:
            print("Kein ESP32-COM-Port erkannt. Der Server sucht automatisch weiter.")

    if not args.no_browser:
        threading.Thread(target=open_browser_when_ready, args=(args.port,), daemon=True).start()

    import local_can_diagnostics

    server_args = ["--host", "127.0.0.1", "--port", str(args.port)]
    if args.demo:
        server_args.append("--demo")
    server_args.extend(["--profile", args.profile])
    if explicit_port:
        server_args.extend(["--serial-port", explicit_port])
    print(f"Starte lokalen Diagnoseserver auf http://127.0.0.1:{args.port}")
    return local_can_diagnostics.main(server_args)


if __name__ == "__main__":
    raise SystemExit(main())
