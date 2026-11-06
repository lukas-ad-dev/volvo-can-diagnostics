#!/usr/bin/env python3
"""Statischer Sicherheitscheck fuer Volvo CAN Control.

Verhindert versehentliche aktive CAN-Funktionen oder das aktive Treiben der
vorbereiteten Ausgaenge. web_ui.cpp wird ausgenommen, weil die dortige
Sicherheitsseite die verbotenen Begriffe nur als Text nennt.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {
    ROOT / "firmware" / "src" / "web_ui.cpp",
    ROOT / "firmware" / "src" / "web_ui.h",
}
FORBIDDEN = [
    ("twai_transmit", "CAN-Senden ist verboten"),
    ("TWAI_MODE_NORMAL", "TWAI darf nur LISTEN_ONLY sein"),
    ("send_message", "Keine CAN-Sendefunktion erlaubt"),
    ("esp_deep_sleep_start", "Kein automatischer Deep Sleep in V0.1"),
    ("digitalWrite(kPinOutput1", "GPIO1 darf in V0.1 nicht aktiv getrieben werden"),
    ("digitalWrite(kPinOutput2", "GPIO2 darf in V0.1 nicht aktiv getrieben werden"),
    ("pinMode(kPinOutput1, OUTPUT)", "GPIO1 muss hochohmig (INPUT) bleiben"),
    ("pinMode(kPinOutput2, OUTPUT)", "GPIO2 muss hochohmig (INPUT) bleiben"),
    ("pinMode(kPinCanTx, OUTPUT)", "Der echte CAN-TXD GPIO15 darf niemals Ausgang sein"),
    ("digitalWrite(kPinCanTx", "Der echte CAN-TXD GPIO15 darf nicht getrieben werden"),
]
REQUIRED = [
    (ROOT / "firmware" / "src" / "can_manager.cpp", "TWAI_MODE_LISTEN_ONLY",
     "TWAI muss ausdruecklich LISTEN_ONLY sein"),
    (ROOT / "firmware" / "src" / "can_manager.cpp", "pinMode(kPinCanTx, INPUT_PULLUP)",
     "GPIO15 muss im Boot/STOP hochgezogen sein"),
    (ROOT / "firmware" / "src" / "can_manager.cpp", "kPinCanTwaiTx",
     "TWAI-TX muss auf den Dummy-Pin gehen"),
    (ROOT / "firmware" / "include" / "app_config.h", "constexpr uint32_t kDefaultBitrateKbps = 500;",
     "Fester Testbetrieb muss 500 kbit/s sein"),
    (ROOT / "firmware" / "include" / "app_config.h", "constexpr uint32_t kSupportedBitrates[] = {500};",
     "Nur 500 kbit/s darf unterstuetzt sein"),
    (ROOT / "firmware" / "src" / "output_control.cpp", "pinMode(kPinOutput1, INPUT)",
     "GPIO1 muss beim Start hochohmig sein"),
    (ROOT / "firmware" / "src" / "output_control.cpp", "pinMode(kPinOutput2, INPUT)",
     "GPIO2 muss beim Start hochohmig sein"),
]


def main() -> int:
    violations = []
    files = []
    for base in (ROOT / "firmware" / "src", ROOT / "firmware" / "lib", ROOT / "firmware" / "include"):
        for path in base.rglob("*"):
            if path.suffix.lower() not in {".c", ".cc", ".cpp", ".h", ".hpp", ".ino"}:
                continue
            if path in SKIP:
                continue
            files.append(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle, reason in FORBIDDEN:
                if needle in text:
                    violations.append(f"{path.relative_to(ROOT)}: {needle!r} ({reason})")

    for path, needle, reason in REQUIRED:
        text = path.read_text(encoding="utf-8", errors="replace")
        if needle not in text:
            violations.append(f"{path.relative_to(ROOT)}: {needle!r} fehlt ({reason})")

    print(f"Geprueft: {len(files)} Quelldateien")
    if violations:
        print("SICHERHEITSVERSTOSS:")
        for violation in violations:
            print(" -", violation)
        return 1
    print("OK: kein CAN-Senden, nur LISTEN_ONLY, 500 kbit/s, echter TXD hochgezogen, Ausgaenge hochohmig.")
    app_text = (ROOT / "firmware" / "include" / "app_config.h").read_text(encoding="utf-8", errors="replace")
    if "constexpr bool kAllowCanStart = true;" in app_text:
        print("WARNUNG: START ist freigegeben (read-only Live-Test); kein Auto-Start, kein Auto-Neuversuch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
