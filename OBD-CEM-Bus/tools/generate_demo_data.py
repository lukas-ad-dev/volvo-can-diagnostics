#!/usr/bin/env python3
"""Erzeugt eine kleine, eindeutig als DEMO markierte NDJSON-Beispieldatei."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo" / "demo_frames.ndjson"


def data_hex(values: list[int]) -> str:
    raw = bytes(values + [0] * (8 - len(values)))
    return raw.hex().upper()


def main() -> None:
    frames = []
    seq = 0
    for t_ms in range(0, 20000, 250):
        camera_on = (t_ms // 15000) % 2 == 1
        ambient_on = (t_ms // 8000) % 2 == 1
        frames.append(
            {
                "type": "can",
                "seq": seq + 1,
                "timestamp_us": t_ms * 1000,
                "id": 0x1A0,
                "id_hex": "0x1A0",
                "extended": False,
                "dlc": 8,
                "data": data_hex([
                    (0x01 if camera_on else 0x00) | (0x02 if ambient_on else 0x00),
                    (seq // 2) & 0xFF,
                    (seq // 512) & 0xFF,
                    0x5A,
                ]),
                "demo": True,
            }
        )
        seq += 1
        if t_ms % 1000 == 0:
            frames.append(
                {
                    "type": "can",
                    "seq": seq + 1,
                    "timestamp_us": t_ms * 1000,
                    "id": 0x3E0,
                    "id_hex": "0x3E0",
                    "extended": False,
                    "dlc": 8,
                    "data": data_hex([0x10 + (seq % 80), 0x33, 0x50, 0x20]),
                    "demo": True,
                }
            )
            seq += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        for frame in frames:
            handle.write(json.dumps(frame, separators=(",", ":")) + "\n")
    print(f"{len(frames)} DEMO-Frames geschrieben: {OUT}")


if __name__ == "__main__":
    main()
