#!/usr/bin/env python3
"""Prueft die Python-Werkzeuge auf CAN-Sende- oder Diagnosefunktionen."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "tools" / "local_can_diagnostics.py",
    ROOT / "tools" / "signal_engine.py",
    ROOT / "tools" / "usb_can_logger.py",
    ROOT / "tools" / "volvo_can_collector.py",
    ROOT / "tools" / "compare_measurements.py",
]
FORBIDDEN = [
    "serial.write", "connection.write", "ser.write", "can.Bus", "python-can",
    "twai_transmit", "send_message", "obd.", "uds.",
]


def main() -> int:
    violations = []
    for path in FILES:
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in FORBIDDEN:
            if needle in text:
                violations.append(f"{path.relative_to(ROOT)}: {needle!r}")
    if violations:
        print("SICHERHEITSVERSTOSS:")
        for violation in violations:
            print(" -", violation)
        return 1
    print(f"OK: {len(FILES)} Python-Dateien ohne CAN-Sende-/Diagnosezugriff.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
