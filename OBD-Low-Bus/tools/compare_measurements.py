#!/usr/bin/env python3
"""Vergleicht zwei CAN-Messungen (CSV) ohne Bedeutungszuweisung.

Beispiel:
    python tools/compare_measurements.py messungen/A.csv messungen/B.csv
    python tools/compare_measurements.py A.csv B.csv --format json --output diff.json

Das Skript zeigt neue/verschwundene CAN-IDs, geaenderte Bytes/Bits,
Variabilitaet und Frequenzaenderungen. Es behauptet nicht, dass eine ID
fuer eine bestimmte Fahrzeugfunktion steht.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

CSV_FIELDS = [
    "can_id",
    "extended",
    "in_a",
    "in_b",
    "count_a",
    "count_b",
    "freq_a",
    "freq_b",
    "freq_delta_pct",
    "data_a",
    "data_b",
    "changed_bytes",
    "changed_bits",
    "variable_a",
    "variable_b",
    "payload_changed",
    "frequency_changed",
    "demo",
]

Key = Tuple[int, bool]


def parse_bool(value: str) -> bool:
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "ja", "ext", "extended"}


def parse_id(row: dict) -> Tuple[int, bool]:
    extended = parse_bool(row.get("extended", "0"))
    raw = str(row.get("can_id_dec") or row.get("can_id") or "0").strip()
    if raw.lower().startswith("0x"):
        return int(raw, 16), extended
    if re.search(r"[A-Fa-f]", raw):
        return int(raw, 16), extended
    return int(raw, 10), extended


def normalize_data(value: str) -> str:
    text = re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()
    return text.ljust(16, "0")[:16]


def id_hex(can_id: int, extended: bool) -> str:
    return f"0x{can_id:0{8 if extended else 3}X}"


class Aggregate:
    def __init__(self, can_id: int, extended: bool) -> None:
        self.can_id = can_id
        self.extended = extended
        self.count = 0
        self.first_us = None
        self.last_us = None
        self.last_data = "0" * 16
        self.last_dlc = 0
        self.max_dlc = 0
        self.or_data = [0] * 8
        self.and_data = [0xFF] * 8
        self.demo = False

    def add(self, timestamp_us: int, dlc: int, data_hex: str, demo: bool) -> None:
        self.count += 1
        self.demo = self.demo or demo
        if self.first_us is None or timestamp_us < self.first_us:
            self.first_us = timestamp_us
        if self.last_us is None or timestamp_us >= self.last_us:
            self.last_us = timestamp_us
            self.last_data = data_hex
            self.last_dlc = dlc
        self.max_dlc = max(self.max_dlc, dlc)
        raw = bytes.fromhex(data_hex)
        for index in range(min(dlc, 8)):
            self.or_data[index] |= raw[index]
            self.and_data[index] &= raw[index]

    def duration_us(self) -> int:
        if self.first_us is None or self.last_us is None:
            return 0
        return max(1, self.last_us - self.first_us)

    def frequency(self) -> float:
        duration = self.duration_us()
        return self.count * 1_000_000.0 / duration if duration else 0.0

    def variable(self) -> List[str]:
        return [
            f"{(self.or_data[i] ^ self.and_data[i]):02X}" if i < self.max_dlc else "00"
            for i in range(8)
        ]


class Measurement:
    def __init__(self, path: Path, label: str, ids: Dict[Key, Aggregate],
                 frames: int, demo_skipped: int) -> None:
        self.path = path
        self.label = label
        self.ids = ids
        self.frames = frames
        self.demo_skipped = demo_skipped

    def start_us(self) -> int:
        values = [entry.first_us for entry in self.ids.values() if entry.first_us is not None]
        return min(values) if values else 0

    def end_us(self) -> int:
        values = [entry.last_us for entry in self.ids.values() if entry.last_us is not None]
        return max(values) if values else 0

    def duration_us(self) -> int:
        if not self.ids:
            return 0
        # Fuer die Frequenz mindestens 1 Sekunde ansetzen, damit einzelne
        # Frames keine unrealistischen Hz-Werte erzeugen.
        return max(1_000_000, self.end_us() - self.start_us())


def load_measurement(path: Path, include_demo: bool = False) -> Measurement:
    ids: Dict[Key, Aggregate] = {}
    frames = 0
    demo_skipped = 0
    label = ""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not label:
                label = (row.get("measurement") or "").strip()
            demo = parse_bool(row.get("demo", "0"))
            if demo and not include_demo:
                demo_skipped += 1
                continue
            can_id, extended = parse_id(row)
            key = (can_id, extended)
            aggregate = ids.get(key)
            if aggregate is None:
                aggregate = Aggregate(can_id, extended)
                ids[key] = aggregate
            aggregate.add(
                int(row.get("timestamp_us") or 0),
                int(row.get("dlc") or 0),
                normalize_data(row.get("data_hex") or row.get("data") or ""),
                demo,
            )
            frames += 1
    if frames == 0 and demo_skipped == 0:
        raise ValueError(f"{path}: keine Daten")
    if not label:
        label = path.stem
    return Measurement(path, label, ids, frames, demo_skipped)


def compare(a: Measurement, b: Measurement) -> dict:
    keys = sorted(set(a.ids) | set(b.ids), key=lambda item: (item[0], item[1]))
    entries = []
    for can_id, extended in keys:
        ea = a.ids.get((can_id, extended))
        eb = b.ids.get((can_id, extended))
        entry = {
            "can_id": can_id,
            "id_hex": id_hex(can_id, extended),
            "extended": extended,
            "in_a": ea is not None,
            "in_b": eb is not None,
            "demo": bool((ea and ea.demo) or (eb and eb.demo)),
            "count_a": ea.count if ea else 0,
            "count_b": eb.count if eb else 0,
            "freq_a": (ea.count * 1_000_000.0 / a.duration_us()) if ea and a.duration_us() else 0.0,
            "freq_b": (eb.count * 1_000_000.0 / b.duration_us()) if eb and b.duration_us() else 0.0,
            "freq_delta_pct": 0.0,
            "data_a": ea.last_data if ea else "0" * 16,
            "data_b": eb.last_data if eb else "0" * 16,
            "dlc_a": ea.last_dlc if ea else 0,
            "dlc_b": eb.last_dlc if eb else 0,
            "changed_bytes": [],
            "variable_a": ea.variable() if ea else ["00"] * 8,
            "variable_b": eb.variable() if eb else ["00"] * 8,
            "payload_changed": False,
            "frequency_changed": False,
        }
        if ea and eb:
            raw_a = bytes.fromhex(entry["data_a"])
            raw_b = bytes.fromhex(entry["data_b"])
            max_dlc = max(ea.last_dlc, eb.last_dlc)
            for index in range(max_dlc):
                xor = raw_a[index] ^ raw_b[index]
                if xor:
                    entry["changed_bytes"].append(
                        {
                            "index": index,
                            "a": f"{raw_a[index]:02X}",
                            "b": f"{raw_b[index]:02X}",
                            "xor": f"{xor:02X}",
                            "bits": [bit for bit in range(8) if xor & (1 << bit)],
                        }
                    )
            entry["payload_changed"] = bool(entry["changed_bytes"]) or ea.last_dlc != eb.last_dlc
            if entry["freq_a"] > 0:
                entry["freq_delta_pct"] = (entry["freq_b"] - entry["freq_a"]) * 100.0 / entry["freq_a"]
            diff = abs(entry["freq_b"] - entry["freq_a"])
            entry["frequency_changed"] = diff > 0.2 and (
                entry["freq_a"] == 0 or abs(entry["freq_delta_pct"]) > 20.0
            )
        entries.append(entry)

    new_ids = [entry for entry in entries if entry["in_b"] and not entry["in_a"]]
    missing_ids = [entry for entry in entries if entry["in_a"] and not entry["in_b"]]
    common = [entry for entry in entries if entry["in_a"] and entry["in_b"]]
    changed = [entry for entry in common if entry["payload_changed"] or entry["frequency_changed"]]
    return {
        "a": {
            "file": str(a.path),
            "label": a.label,
            "frames": a.frames,
            "demo_skipped": a.demo_skipped,
            "duration_ms": a.duration_us() / 1000.0,
            "ids": len(a.ids),
        },
        "b": {
            "file": str(b.path),
            "label": b.label,
            "frames": b.frames,
            "demo_skipped": b.demo_skipped,
            "duration_ms": b.duration_us() / 1000.0,
            "ids": len(b.ids),
        },
        "new_ids": new_ids,
        "missing_ids": missing_ids,
        "common": common,
        "changed": changed,
        "entries": entries,
    }


def output_table(result: dict) -> None:
    print(f"Messung A: {result['a']['label']} ({result['a']['frames']} Frames, {result['a']['duration_ms']/1000:.2f} s)")
    print(f"Messung B: {result['b']['label']} ({result['b']['frames']} Frames, {result['b']['duration_ms']/1000:.2f} s)")
    if result["a"]["demo_skipped"] or result["b"]["demo_skipped"]:
        print(f"DEMO-Frames ignoriert: A={result['a']['demo_skipped']}, B={result['b']['demo_skipped']}")
    print(f"Neu in B: {len(result['new_ids'])} | Nur in A: {len(result['missing_ids'])} | "
          f"Gemeinsam geaendert: {len(result['changed'])}")
    print()
    print("Neu in B:")
    for entry in result["new_ids"]:
        print(f"  {entry['id_hex']:>10}  {entry['count_b']:6} Frames  {entry['freq_b']:7.2f} Hz")
    print("Nur in A:")
    for entry in result["missing_ids"]:
        print(f"  {entry['id_hex']:>10}  {entry['count_a']:6} Frames  {entry['freq_a']:7.2f} Hz")
    print()
    print("Gemeinsame IDs mit Aenderungen:")
    if not result["changed"]:
        print("  keine erkannt")
    for entry in result["changed"]:
        changes = []
        for change in entry["changed_bytes"]:
            bits = ",".join(str(bit) for bit in change["bits"])
            changes.append(f"Byte {change['index']} {change['a']}->{change['b']} (Bits {bits})")
        if entry["frequency_changed"]:
            changes.append(f"Frequenz {entry['freq_a']:.2f}->{entry['freq_b']:.2f} Hz")
        print(
            f"  {entry['id_hex']:>10}  A={entry['data_a']} B={entry['data_b']}  "
            f"| {'; '.join(changes) if changes else 'nur Variabilitaet'}"
        )
        if any(value != "00" for value in entry["variable_a"] + entry["variable_b"]):
            print(f"      variabel A={''.join(entry['variable_a'])} B={''.join(entry['variable_b'])}")
    print()
    print("Hinweis: Keine automatische Bedeutungszuweisung. IDs/Bits muessen experimentell bestaetigt werden.")


def output_csv(result: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_FIELDS)
        for entry in result["entries"]:
            writer.writerow([
                entry["id_hex"],
                1 if entry["extended"] else 0,
                1 if entry["in_a"] else 0,
                1 if entry["in_b"] else 0,
                entry["count_a"],
                entry["count_b"],
                f"{entry['freq_a']:.4f}",
                f"{entry['freq_b']:.4f}",
                f"{entry['freq_delta_pct']:.2f}",
                entry["data_a"],
                entry["data_b"],
                "".join(f"{change['index']:X}" for change in entry["changed_bytes"]),
                "".join(change["xor"] for change in entry["changed_bytes"]),
                "".join(entry["variable_a"]),
                "".join(entry["variable_b"]),
                1 if entry["payload_changed"] else 0,
                1 if entry["frequency_changed"] else 0,
                1 if entry["demo"] else 0,
            ])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CAN-Messungen vergleichen")
    parser.add_argument("a", type=Path, help="Messung A (CSV)")
    parser.add_argument("b", type=Path, help="Messung B (CSV)")
    parser.add_argument("--format", choices=["table", "json", "csv"], default="table")
    parser.add_argument("--output", type=Path, help="Zieldatei fuer JSON/CSV")
    parser.add_argument("--include-demo", action="store_true", help="DEMO-Frames mit auswerten")
    args = parser.parse_args(argv)

    try:
        measurement_a = load_measurement(args.a, args.include_demo)
        measurement_b = load_measurement(args.b, args.include_demo)
    except (OSError, ValueError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 2

    result = compare(measurement_a, measurement_b)
    if args.format == "table":
        output_table(result)
    elif args.format == "json":
        text = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(text, encoding="utf-8")
            print(f"JSON geschrieben: {args.output}")
        else:
            print(text)
    else:
        if args.output is None:
            args.output = Path("vergleich.csv")
        output_csv(result, args.output)
        print(f"CSV geschrieben: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
