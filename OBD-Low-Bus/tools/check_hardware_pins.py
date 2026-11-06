#!/usr/bin/env python3
"""Automatischer Test der zentralen Hardwarebelegung.

Bestaetigte Waveshare-Belegung (Schaltplan + WS_GPIO.h, 04.11.2026):
CAN TX=GPIO15, CAN RX=GPIO16, RS485 TX=GPIO17, RS485 RX=GPIO18.
Der Test schuetzt davor, dass CAN versehentlich wieder auf GPIO17/18 gelegt wird.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS_HEADER = ROOT / "firmware" / "lib" / "volvo_core" / "include" / "volvo_core" / "hardware_pins.h"
CAN_SOURCE = ROOT / "firmware" / "src" / "can_manager.cpp"

EXPECTED = {
    "CanTx": 15,
    "CanRx": 16,
    "Rs485Tx": 17,
    "Rs485Rx": 18,
}


def main() -> int:
    errors: list[str] = []
    text = PINS_HEADER.read_text(encoding="utf-8")
    found = {
        name: int(value)
        for name, value in re.findall(
            r"constexpr\s+uint8_t\s+k(CanTx|CanRx|Rs485Tx|Rs485Rx)\s*=\s*(\d+)\s*;", text
        )
    }
    print("Gefundene zentrale Pins:", found)
    for name, expected in EXPECTED.items():
        if found.get(name) != expected:
            errors.append(f"{name}: erwartet {expected}, gefunden {found.get(name)}")

    can_text = CAN_SOURCE.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", can_text)
    if "TWAI_MODE_LISTEN_ONLY" not in normalized:
        errors.append("can_manager.cpp: TWAI_MODE_LISTEN_ONLY fehlt")
    if not re.search(
        r"TWAI_GENERAL_CONFIG_DEFAULT\(\s*static_cast<gpio_num_t>\(kPinCanTx\),\s*"
        r"static_cast<gpio_num_t>\(kPinCanRx\),\s*TWAI_MODE_LISTEN_ONLY\s*\)",
        normalized,
    ):
        errors.append("can_manager.cpp: TWAI nutzt nicht kPinCanTx/kPinCanRx oder nicht LISTEN_ONLY")
    if "TWAI_MODE_NORMAL" in normalized:
        errors.append("can_manager.cpp: TWAI_MODE_NORMAL ist verboten")
    if re.search(r"TWAI_GENERAL_CONFIG_DEFAULT\(\s*(?:static_cast<gpio_num_t>\()?\s*(?:17|18)\b", normalized):
        errors.append("can_manager.cpp: TWAI verwendet rohe Pins 17/18")

    for path in list((ROOT / "firmware" / "src").rglob("*")) + list((ROOT / "firmware" / "include").rglob("*")):
        if path.suffix.lower() not in {".c", ".cc", ".cpp", ".h", ".hpp"}:
            continue
        if path.name in {"web_ui.cpp", "web_ui.h"}:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            if "kPinCanTx" in line and re.search(r"=\s*17\b", line):
                errors.append(f"{path.relative_to(ROOT)}: kPinCanTx=17 gefunden")
            if "kPinCanRx" in line and re.search(r"=\s*18\b", line):
                errors.append(f"{path.relative_to(ROOT)}: kPinCanRx=18 gefunden")

    if errors:
        print("HARDWARE-PIN-TEST FEHLGESCHLAGEN:")
        for error in errors:
            print(" -", error)
        return 1
    print("OK: CAN TX=GPIO15, CAN RX=GPIO16, RS485 TX=GPIO17, RS485 RX=GPIO18; TWAI nur LISTEN_ONLY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
