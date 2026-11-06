#!/usr/bin/env python3
"""Prueft die statischen Flash-/PSRAM-Einstellungen fuer das Waveshare-Board."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    "platform = espressif32@8.0.0",
    "board = esp32-s3-devkitc-1",
    "board_build.flash_size = 16MB",
    "board_upload.flash_size = 16MB",
    "board_upload.maximum_size = 16777216",
    "board_build.arduino.memory_type = qio_opi",
    "board_build.partitions = partitions.csv",
    "-DARDUINO_USB_CDC_ON_BOOT=1",
    "-DARDUINO_USB_MODE=1",
]


def main() -> int:
    config = (ROOT / "firmware" / "platformio.ini").read_text(encoding="utf-8")
    missing = [line for line in EXPECTED if line not in config]
    if missing:
        print("FEHLENDE BOARD-EINSTELLUNGEN:")
        for line in missing:
            print(" -", line)
        return 1

    partitions = (ROOT / "firmware" / "partitions.csv").read_text(encoding="utf-8")
    required = ["app0,", "0x10000,", "0x400000,", "app1,", "0x410000,", "0x400000,"]
    missing_parts = [item for item in required if item not in partitions]
    if missing_parts:
        print("Partitionstabelle unerwartet:", missing_parts)
        return 1

    print("OK: 16 MB Flash, OPI-PSRAM (qio_opi), USB-CDC, 2x 4-MB-App-Partition.")
    print("Hinweis: Die tatsaechliche PSRAM-Erkennung ist nur auf dem Board pruefbar")
    print("         (Firmware gibt freien PSRAM im Serial Monitor aus).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
