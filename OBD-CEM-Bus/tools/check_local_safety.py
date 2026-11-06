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
    "serial.write", "ser.write", "can.Bus", "python-can",
    "twai_transmit", "send_message", "obd.", "uds.",
]


def main() -> int:
    violations = []
    for path in FILES:
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in FORBIDDEN:
            if needle in text:
                violations.append(f"{path.relative_to(ROOT)}: {needle!r}")
    local = (ROOT / "tools" / "local_can_diagnostics.py").read_text(encoding="utf-8", errors="replace")
    for line in local.splitlines():
        if "connection.write" not in line:
            continue
        if not any(token in line for token in ("STATUS", "TWAI", "command")):
            violations.append(
                f"tools/local_can_diagnostics.py: unerlaubter Serial-Write: {line.strip()!r}"
            )
    if 'return self._send_can_command("START")' not in local:
        violations.append("tools/local_can_diagnostics.py: can_start sendet nicht exakt START")
    if 'return self._send_can_command("STOP")' not in local:
        violations.append("tools/local_can_diagnostics.py: can_stop sendet nicht exakt STOP")
    if violations:
        print("SICHERHEITSVERSTOSS:")
        for violation in violations:
            print(" -", violation)
        return 1
    print(f"OK: {len(FILES)} Python-Dateien ohne CAN-Sende-/Diagnosezugriff.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
