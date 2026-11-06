#!/usr/bin/env python3
"""Volvo CAN Control - CSV-Collector fuer Windows.

Verbindet sich mit dem ESP32 (TCP-Port 81), liest NDJSON-Frames und
schreibt sie fortlaufend in eine CSV-Datei. Nur Python-Standardbibliothek.

Beispiel:
    python tools\\volvo_can_collector.py --host 192.168.4.1 --port 81 --output messung.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

FIELDS = [
    "seq",
    "timestamp_us",
    "can_id",
    "can_id_dec",
    "extended",
    "dlc",
    "data_hex",
    "demo",
    "received_iso",
]


def parse_frame(line: str) -> Optional[dict]:
    """Parst eine NDJSON-Zeile; ungueltige Zeilen ergeben None."""
    line = line.strip()
    if not line:
        return None
    if line.startswith("#"):
        return None
    try:
        frame = json.loads(line)
    except json.JSONDecodeError:
        return None
    required = {"seq", "timestamp_us", "id", "extended", "dlc", "data", "demo"}
    if not required.issubset(frame):
        return None
    return frame


def frame_row(frame: dict) -> List[object]:
    """Wandelt einen Frame in eine CSV-Zeile um."""
    can_id = int(frame["id"])
    extended = bool(frame["extended"])
    width = 8 if extended else 3
    id_hex = f"0x{can_id:0{width}X}"
    return [
        int(frame["seq"]),
        int(frame["timestamp_us"]),
        id_hex,
        can_id,
        1 if extended else 0,
        int(frame["dlc"]),
        str(frame["data"]),
        1 if frame["demo"] else 0,
        datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    ]


def connect(host: str, port: int, timeout: float = 5.0) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.settimeout(30.0)
    return sock


def run(host: str, port: int, output: Path, quiet: bool = False, max_frames: int = 0) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    new_file = not output.exists() or output.stat().st_size == 0
    total = 0

    with output.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=",", lineterminator="\n")
        if new_file:
            writer.writerow(FIELDS)
            handle.flush()

        done = False
        while not done:
            try:
                if not quiet:
                    print(f"Verbinde mit {host}:{port} ...", flush=True)
                with connect(host, port) as sock:
                    if not quiet:
                        print("Verbunden. Strg+C beendet die Aufzeichnung.", flush=True)
                    reader = sock.makefile("r", encoding="utf-8", newline="\n")
                    while True:
                        line = reader.readline()
                        if not line:
                            raise ConnectionError("Verbindung vom ESP beendet")
                        frame = parse_frame(line)
                        if frame is None:
                            continue
                        writer.writerow(frame_row(frame))
                        total += 1
                        if total % 25 == 0:
                            handle.flush()
                        if not quiet and total % 500 == 0:
                            print(f"{total} Frames gespeichert ...", flush=True)
                        if max_frames and total >= max_frames:
                            done = True
                            break
            except KeyboardInterrupt:
                print("\nAufzeichnung beendet.", flush=True)
                break
            except (OSError, ConnectionError) as error:
                if not quiet:
                    print(f"Verbindungsfehler: {error}. Neuer Versuch in 2 s ...", flush=True)
                time.sleep(2.0)
            finally:
                handle.flush()

    print(f"CSV gespeichert: {output} ({total} Frames)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Volvo CAN Control CSV-Collector")
    parser.add_argument("--host", default="192.168.4.1", help="IP des ESP32 (Standard: 192.168.4.1)")
    parser.add_argument("--port", type=int, default=81, help="TCP-Port des NDJSON-Streams (Standard: 81)")
    parser.add_argument("--output", default=None, help="Ziel-CSV (Standard: volvo-can-messung-<Zeit>.csv)")
    parser.add_argument("--quiet", action="store_true", help="Weniger Konsolenausgaben")
    parser.add_argument("--max-frames", type=int, default=0, help="Nach so vielen Frames beenden (0 = unbegrenzt, fuer Tests)")
    args = parser.parse_args(argv)

    if args.output:
        output = Path(args.output)
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = Path(f"volvo-can-messung-{stamp}.csv")

    try:
        return run(args.host, args.port, output, args.quiet, args.max_frames)
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
