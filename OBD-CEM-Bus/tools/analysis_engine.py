"""Offline-/Live-Analyse fuer CAN-Rohdaten.

Die Engine liest ausschliesslich vorhandene JSONL-Aufzeichnungen. Sie sendet
keine CAN-Nachrichten und benoetigt keinen angeschlossenen Bus.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from signal_engine import data_bytes, frame_id, normalize_data

MAX_BITS = 60
DEFAULT_BEFORE_S = 2.0
DEFAULT_AFTER_S = 5.0
DEFAULT_MAX_GAP_S = 120.0


def parse_iso(value: Any) -> Optional[float]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (ValueError, TypeError):
        return None


def iso_to_text(epoch: Optional[float]) -> str:
    if epoch is None:
        return ""
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="milliseconds")


def _id_hex(can_id: int, extended: bool) -> str:
    return f"0x{can_id:0{8 if extended else 3}X}"


def resolve_session(output_dir: Path, relative: str) -> Tuple[Path, Path]:
    output_dir = output_dir.resolve()
    raw_path = (output_dir / relative).resolve()
    if output_dir not in raw_path.parents or not raw_path.is_file():
        raise ValueError("Session nicht gefunden")
    if not raw_path.name.endswith("_raw.jsonl"):
        raise ValueError("Ungueltige Session-Datei")
    events_path = raw_path.with_name(raw_path.name.replace("_raw.jsonl", "_events.jsonl"))
    return raw_path, events_path


def list_sessions(output_dir: Path, current_raw: Optional[Path] = None) -> List[dict]:
    output_dir = Path(output_dir)
    current = Path(current_raw).resolve() if current_raw else None
    sessions = []
    for raw_path in output_dir.rglob("*_raw.jsonl"):
        try:
            resolved = raw_path.resolve()
            if output_dir.resolve() not in resolved.parents:
                continue
            stat = resolved.stat()
            events_path = resolved.with_name(resolved.name.replace("_raw.jsonl", "_events.jsonl"))
            label = resolved.relative_to(output_dir.resolve()).as_posix()
            sessions.append({
                "session": label,
                "name": resolved.parent.name if resolved.name == "session_raw.jsonl" else resolved.name.replace("_raw.jsonl", ""),
                "raw": label,
                "events": events_path.relative_to(output_dir.resolve()).as_posix() if events_path.exists() else "",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "current": current is not None and resolved == current,
            })
        except (OSError, ValueError):
            continue
    sessions.sort(key=lambda item: (not item["current"], -item["modified"]))
    return sessions


def _iter_frames(raw_path: Path, start: Optional[float] = None, end: Optional[float] = None) -> Iterable[dict]:
    with open(raw_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("type") != "frame":
                continue
            if start is not None or end is not None:
                stamp = parse_iso(item.get("received_iso"))
                if stamp is None:
                    continue
                if start is not None and stamp < start:
                    continue
                if end is not None and stamp > end:
                    continue
            yield item


def _new_bit() -> dict:
    return {
        "samples": 0,
        "ones": 0,
        "changes": 0,
        "last": None,
        "first_change": None,
        "last_change": None,
        "intervals": [],
    }


def _new_id(can_id: int, extended: bool) -> dict:
    return {
        "can_id": can_id,
        "extended": extended,
        "id_hex": _id_hex(can_id, extended),
        "frames": 0,
        "dlc": 0,
        "latest_data": "",
        "first_iso": "",
        "last_iso": "",
        "bytes": [[_new_bit() for _ in range(8)] for _ in range(8)],
    }


def _update_bit(bit: dict, value: int, stamp: float) -> None:
    bit["samples"] += 1
    bit["ones"] += value
    if bit["last"] is not None and bit["last"] != value:
        bit["changes"] += 1
        if bit["first_change"] is None:
            bit["first_change"] = stamp
        if bit["last_change"] is not None:
            intervals = bit["intervals"]
            intervals.append(stamp - bit["last_change"])
            if len(intervals) > 80:
                del intervals[:20]
        bit["last_change"] = stamp
    bit["last"] = value


def _periodic(bit: dict) -> bool:
    intervals = bit["intervals"]
    if len(intervals) < 5:
        return False
    mean = sum(intervals) / len(intervals)
    if mean <= 0:
        return False
    variance = sum((value - mean) ** 2 for value in intervals) / len(intervals)
    return math.sqrt(variance) / mean < 0.35


def _bit_summary(bit: dict, dlc: int, byte: int, bit_index: int) -> dict:
    samples = bit["samples"]
    ones = bit["ones"]
    if not samples or byte >= dlc:
        return {
            "byte": byte,
            "bit": bit_index,
            "samples": 0,
            "value": None,
            "stable": False,
            "changing": False,
            "periodic": False,
            "changes": 0,
            "purity": None,
            "first_change_s": None,
            "last_change_s": None,
            "mean_interval_ms": None,
            "change_rate_hz": 0.0,
            "padding": True,
        }
    value = 1 if ones == samples else 0 if ones == 0 else None
    purity = max(ones, samples - ones) / samples
    intervals = bit["intervals"]
    mean_interval = sum(intervals) / len(intervals) if intervals else None
    return {
        "byte": byte,
        "bit": bit_index,
        "samples": samples,
        "value": value,
        "stable": value is not None,
        "changing": bit["changes"] > 0,
        "periodic": _periodic(bit),
        "changes": bit["changes"],
        "purity": round(purity, 4),
        "counter_suspect": bit["changes"] >= max(5, int(samples * 0.08)) or _periodic(bit),
        "first_change_s": round(bit["first_change"], 3) if bit["first_change"] is not None else None,
        "last_change_s": round(bit["last_change"], 3) if bit["last_change"] is not None else None,
        "mean_interval_ms": round(mean_interval * 1000, 1) if mean_interval else None,
        "change_rate_hz": round(1.0 / mean_interval, 2) if mean_interval and mean_interval > 0 else 0.0,
        "padding": False,
    }


def overview(raw_path: Path, id_filter: str = "", max_frames: Optional[int] = None) -> dict:
    ids: Dict[Tuple[int, bool], dict] = {}
    count = 0
    needle = id_filter.strip().lower().replace("0x", "")
    for frame in _iter_frames(raw_path):
        try:
            can_id, extended = frame_id(frame)
        except ValueError:
            continue
        id_hex = _id_hex(can_id, extended)
        if needle and needle not in id_hex.lower().replace("0x", "") and needle != str(can_id):
            continue
        key = (can_id, extended)
        entry = ids.get(key)
        if entry is None:
            entry = _new_id(can_id, extended)
            ids[key] = entry
        payload = data_bytes(frame)
        dlc = min(int(frame.get("dlc", 0)), len(payload), 8)
        stamp = float(frame.get("timestamp_us", 0)) / 1_000_000.0
        entry["frames"] += 1
        entry["dlc"] = max(entry["dlc"], dlc)
        entry["latest_data"] = normalize_data(payload)
        entry["last_iso"] = str(frame.get("received_iso", ""))
        if not entry["first_iso"]:
            entry["first_iso"] = entry["last_iso"]
        for byte in range(dlc):
            value_byte = payload[byte]
            for bit_index in range(8):
                _update_bit(entry["bytes"][byte][bit_index], (value_byte >> bit_index) & 1, stamp)
        count += 1
        if max_frames and count >= max_frames:
            break
    result = []
    for entry in sorted(ids.values(), key=lambda item: (item["can_id"], item["extended"])):
        dlc = entry["dlc"]
        bytes_data = []
        changing = 0
        for byte in range(8):
            if byte < dlc:
                bits = [
                    _bit_summary(entry["bytes"][byte][bit_index], dlc, byte, bit_index)
                    for bit_index in range(8)
                ]
                changing += sum(1 for bit in bits if bit["changing"])
            else:
                bits = [
                    {
                        "byte": byte,
                        "bit": bit_index,
                        "samples": 0,
                        "value": None,
                        "stable": False,
                        "changing": False,
                        "periodic": False,
                        "changes": 0,
                        "purity": None,
                        "first_change_iso": "",
                        "last_change_iso": "",
                        "mean_interval_ms": None,
                        "change_rate_hz": 0.0,
                        "padding": True,
                    }
                    for bit_index in range(8)
                ]
            bytes_data.append({
                "byte": byte,
                "bits": bits,
            })
        result.append({
            "can_id": entry["can_id"],
            "extended": entry["extended"],
            "id_hex": entry["id_hex"],
            "frames": entry["frames"],
            "dlc": dlc,
            "latest_data": entry["latest_data"],
            "first_iso": entry["first_iso"],
            "last_iso": entry["last_iso"],
            "changing_bits": changing,
            "bytes": bytes_data,
        })
    return {"ids": result, "frames": count}


def load_events(events_path: Path) -> List[dict]:
    events = []
    if not events_path.exists():
        return events
    with open(events_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind", ""))
            if kind.startswith("firmware") or kind in {"diag", "raw", "connection", "signal_change"}:
                continue
            label = item.get("label") or item.get("action_label") or ""
            if not label or str(label).startswith("#"):
                continue
            stamp = item.get("timestamp")
            epoch = parse_iso(stamp)
            if epoch is None:
                continue
            events.append({
                "id": item.get("id"),
                "kind": item.get("kind", ""),
                "label": str(label),
                "timestamp": str(stamp),
                "epoch": epoch,
                "measurement": item.get("measurement", ""),
            })
    events.sort(key=lambda item: item["epoch"])
    return events


def _label_key(value: str) -> str:
    return " ".join(value.strip().lower().split())


def pair_events(events: List[dict], label_a: str, label_b: str,
                before_s: float, after_s: float, max_gap_s: float) -> List[dict]:
    key_a = _label_key(label_a)
    key_b = _label_key(label_b)
    if not key_a or not key_b:
        return []
    a_events = [event for event in events if _label_key(event["label"]) == key_a]
    b_events = [event for event in events if _label_key(event["label"]) == key_b]
    pairs = []
    used_b = set()
    for index, event_a in enumerate(a_events):
        candidates = [
            (b_index, event_b) for b_index, event_b in enumerate(b_events)
            if b_index not in used_b and event_b["epoch"] > event_a["epoch"]
            and event_b["epoch"] - event_a["epoch"] <= max_gap_s
        ]
        if not candidates:
            continue
        b_index, event_b = min(candidates, key=lambda item: item[1]["epoch"])
        used_b.add(b_index)
        next_a = next((event["epoch"] for event in a_events if event["epoch"] > event_b["epoch"]), None)
        a_start = event_a["epoch"] + 0.05
        a_end = min(event_a["epoch"] + after_s, event_b["epoch"] - 0.05)
        b_start = event_b["epoch"] + 0.05
        b_end = event_b["epoch"] + after_s
        if next_a is not None:
            b_end = min(b_end, next_a - 0.05)
        if a_end - a_start < 0.2 or b_end - b_start < 0.2:
            continue
        pairs.append({
            "index": len(pairs) + 1,
            "label_a": event_a["label"],
            "label_b": event_b["label"],
            "a_marker": event_a["timestamp"],
            "b_marker": event_b["timestamp"],
            "a_start": iso_to_text(a_start),
            "a_end": iso_to_text(a_end),
            "b_start": iso_to_text(b_start),
            "b_end": iso_to_text(b_end),
            "chart_start": iso_to_text(event_a["epoch"] - before_s),
            "chart_end": iso_to_text(b_end),
            "a_epoch_start": a_start,
            "a_epoch_end": a_end,
            "b_epoch_start": b_start,
            "b_epoch_end": b_end,
        })
    return pairs


def _definitions(index: Optional[List[dict]]) -> List[dict]:
    return index or []


def _meaning(definitions: List[dict], can_id: int, extended: bool, byte: int, bit: int) -> dict:
    for definition in definitions:
        try:
            if int(definition.get("can_id", -1)) != can_id:
                continue
            if bool(definition.get("extended", False)) != extended:
                continue
            if int(definition.get("byte", -1)) != byte:
                continue
            if int(definition.get("bit_mask", 0) or 0) & (1 << bit):
                return {
                    "name": definition.get("name", ""),
                    "id": definition.get("id", ""),
                    "status": definition.get("status", "unknown"),
                }
        except (TypeError, ValueError):
            continue
    return {}


def _pair_bit_data() -> dict:
    return {"samples": 0, "ones": 0, "changes": 0, "last": None, "last_stamp": None, "intervals": []}


def _update_pair_bit(bit: dict, value: int, stamp: float) -> None:
    bit["samples"] += 1
    bit["ones"] += value
    if bit["last"] is not None and bit["last"] != value:
        bit["changes"] += 1
        if bit["last_stamp"] is not None:
            bit["intervals"].append(stamp - bit["last_stamp"])
        bit["last_stamp"] = stamp
    elif bit["last_stamp"] is None:
        bit["last_stamp"] = stamp
    bit["last"] = value


def analyze(raw_path: Path, events_path: Path, label_a: str, label_b: str,
            before_s: float = DEFAULT_BEFORE_S, after_s: float = DEFAULT_AFTER_S,
            max_gap_s: float = DEFAULT_MAX_GAP_S,
            filters: Optional[dict] = None,
            definitions: Optional[List[dict]] = None) -> dict:
    filters = filters or {}
    events = load_events(events_path)
    pairs = pair_events(events, label_a, label_b, before_s, after_s, max_gap_s)
    if not pairs:
        return {
            "pairs": [],
            "candidates": [],
            "wakeup_ids": [],
            "filters": filters,
            "message": "Keine passenden A/B-Marker gefunden. Erst Marker setzen oder andere Labels waehlen.",
        }

    windows = []
    for pair in pairs:
        windows.append((pair["a_epoch_start"], pair["a_epoch_end"], pair["index"], "A"))
        windows.append((pair["b_epoch_start"], pair["b_epoch_end"], pair["index"], "B"))

    pair_state: Dict[Tuple[int, str], Dict[Tuple[int, bool], dict]] = defaultdict(dict)
    id_presence: Dict[Tuple[int, str], Dict[Tuple[int, bool], int]] = defaultdict(Counter)

    for frame in _iter_frames(raw_path):
        stamp = parse_iso(frame.get("received_iso"))
        if stamp is None:
            continue
        active = [window for window in windows if window[0] <= stamp <= window[1]]
        if not active:
            continue
        try:
            can_id, extended = frame_id(frame)
        except ValueError:
            continue
        payload = data_bytes(frame)
        dlc = min(int(frame.get("dlc", 0)), len(payload), 8)
        for _, _, pair_index, state in active:
            key = (pair_index, state)
            state_data = pair_state[key]
            id_key = (can_id, extended)
            id_presence[key][id_key] += 1
            entry = state_data.get(id_key)
            if entry is None:
                entry = {"frames": 0, "dlc": 0, "bits": [[_pair_bit_data() for _ in range(8)] for _ in range(8)]}
                state_data[id_key] = entry
            entry["frames"] += 1
            entry["dlc"] = max(entry["dlc"], dlc)
            for byte in range(dlc):
                value_byte = payload[byte]
                for bit_index in range(8):
                    _update_pair_bit(entry["bits"][byte][bit_index], (value_byte >> bit_index) & 1, stamp)

    all_ids = set()
    for state_data in pair_state.values():
        all_ids.update(state_data.keys())
    pair_count = len(pairs)
    candidate_bits = []
    wakeup_ids = []
    for can_id, extended in sorted(all_ids):
        present_a = 0
        present_b = 0
        for pair in pairs:
            index = pair["index"]
            if (can_id, extended) in pair_state[(index, "A")]:
                present_a += 1
            if (can_id, extended) in pair_state[(index, "B")]:
                present_b += 1
        if present_a != present_b:
            wakeup_ids.append({
                "can_id": can_id,
                "extended": extended,
                "id_hex": _id_hex(can_id, extended),
                "pairs_a": present_a,
                "pairs_b": present_b,
                "reason": "ID nur in einem Zustand vorhanden",
            })
        max_dlc = 0
        for pair in pairs:
            for state in ("A", "B"):
                entry = pair_state[(pair["index"], state)].get((can_id, extended))
                if entry:
                    max_dlc = max(max_dlc, entry["dlc"])
        for byte in range(max_dlc):
            byte_changes = [0] * 8
            for bit_index in range(8):
                a_values = Counter()
                b_values = Counter()
                a_purity = []
                b_purity = []
                changes = 0
                intervals = []
                a_samples = 0
                b_samples = 0
                stable_pairs = 0
                inconsistent_pairs = 0
                for pair in pairs:
                    a_entry = pair_state[(pair["index"], "A")].get((can_id, extended))
                    b_entry = pair_state[(pair["index"], "B")].get((can_id, extended))
                    if not a_entry or not b_entry:
                        continue
                    if byte >= a_entry["dlc"] or byte >= b_entry["dlc"]:
                        continue
                    a_bit = a_entry["bits"][byte][bit_index]
                    b_bit = b_entry["bits"][byte][bit_index]
                    if not a_bit["samples"] or not b_bit["samples"]:
                        continue
                    a_val = 1 if a_bit["ones"] == a_bit["samples"] else 0 if a_bit["ones"] == 0 else None
                    b_val = 1 if b_bit["ones"] == b_bit["samples"] else 0 if b_bit["ones"] == 0 else None
                    a_samples += a_bit["samples"]
                    b_samples += b_bit["samples"]
                    changes += a_bit["changes"] + b_bit["changes"]
                    intervals.extend(a_bit["intervals"])
                    intervals.extend(b_bit["intervals"])
                    if a_val is not None and b_val is not None and a_val != b_val:
                        stable_pairs += 1
                        a_values[a_val] += 1
                        b_values[b_val] += 1
                    else:
                        inconsistent_pairs += 1
                    a_purity.append(max(a_bit["ones"], a_bit["samples"] - a_bit["ones"]) / a_bit["samples"])
                    b_purity.append(max(b_bit["ones"], b_bit["samples"] - b_bit["ones"]) / b_bit["samples"])
                if stable_pairs == 0:
                    continue
                a_value = a_values.most_common(1)[0][0]
                b_value = b_values.most_common(1)[0][0]
                consistency = stable_pairs / max(1, stable_pairs + inconsistent_pairs)
                purity = (sum(a_purity) + sum(b_purity)) / max(1, len(a_purity) + len(b_purity))
                correlation = round(100 * consistency * purity, 1)
                if correlation <= 0:
                    continue
                periodic = False
                if len(intervals) >= 5:
                    mean = sum(intervals) / len(intervals)
                    if mean > 0:
                        variance = sum((item - mean) ** 2 for item in intervals) / len(intervals)
                        periodic = math.sqrt(variance) / mean < 0.35
                counter = changes >= max(4, int((a_samples + b_samples) * 0.08)) or periodic
                confidence = "hoch" if stable_pairs >= 2 and correlation >= 90 and purity >= 0.95 else "mittel" if correlation >= 80 else "niedrig"
                material = _meaning(_definitions(definitions), can_id, extended, byte, bit_index)
                candidate_bits.append({
                    "type": "bit",
                    "can_id": can_id,
                    "extended": extended,
                    "id_hex": _id_hex(can_id, extended),
                    "byte": byte,
                    "bit": bit_index,
                    "mask": 1 << bit_index,
                    "a_value": a_value,
                    "b_value": b_value,
                    "changes": changes,
                    "correlation": correlation,
                    "confidence": confidence,
                    "pairs_consistent": stable_pairs,
                    "pairs_total": len(pairs),
                    "a_samples": a_samples,
                    "b_samples": b_samples,
                    "periodic": periodic,
                    "counter_suspect": counter,
                    "wakeup": False,
                    "one_shot": stable_pairs == 1,
                    "meaning": material.get("name", ""),
                    "signal_id": material.get("id", ""),
                    "signal_status": material.get("status", ""),
                })
                byte_changes[bit_index] = changes

            # Mehrbitiges Byte-Feld, wenn mindestens zwei Bits korrelieren.
            bits_here = [
                item for item in candidate_bits
                if item["can_id"] == can_id and item["extended"] == extended
                and item["byte"] == byte and item["type"] == "bit"
            ]
            if len(bits_here) >= 2:
                mask = 0
                a_val = 0
                b_val = 0
                for item in bits_here:
                    mask |= item["mask"]
                    a_val |= item["a_value"] << item["bit"]
                    b_val |= item["b_value"] << item["bit"]
                candidate_bits.append({
                    "type": "byte",
                    "can_id": can_id,
                    "extended": extended,
                    "id_hex": _id_hex(can_id, extended),
                    "byte": byte,
                    "bit": None,
                    "mask": mask,
                    "a_value": a_val,
                    "b_value": b_val,
                    "changes": sum(item["changes"] for item in bits_here),
                    "correlation": round(min(item["correlation"] for item in bits_here), 1),
                    "confidence": "mittel" if any(item["confidence"] == "hoch" for item in bits_here) else "niedrig",
                    "pairs_consistent": min(item["pairs_consistent"] for item in bits_here),
                    "pairs_total": len(pairs),
                    "a_samples": sum(item["a_samples"] for item in bits_here),
                    "b_samples": sum(item["b_samples"] for item in bits_here),
                    "periodic": any(item["periodic"] for item in bits_here),
                    "counter_suspect": any(item["counter_suspect"] for item in bits_here) or len(bits_here) >= 3,
                    "wakeup": False,
                    "one_shot": all(item["one_shot"] for item in bits_here),
                    "meaning": "",
                    "signal_id": "",
                    "signal_status": "",
                    "bit_count": len(bits_here),
                })

    # Checksum-/Counter-Verdacht fuer Bytes mit vielen wechselnden Bits.
    by_byte = defaultdict(list)
    for item in candidate_bits:
        if item["type"] == "bit":
            by_byte[(item["can_id"], item["extended"], item["byte"])].append(item)
    for items in by_byte.values():
        if len(items) >= 3:
            for item in items:
                item["checksum_suspect"] = True

    for item in candidate_bits:
        item.setdefault("checksum_suspect", False)

    filter_id = str(filters.get("id", "")).strip().lower().replace("0x", "")
    filter_byte = filters.get("byte")
    filter_bit = filters.get("bit")
    min_corr = float(filters.get("min_correlation", 0) or 0)
    hide_counters = bool(filters.get("hide_counters", False))
    hide_wakeup = bool(filters.get("hide_wakeup", False))
    stable_only = bool(filters.get("stable_only", False))
    result = []
    for item in candidate_bits:
        if filter_id and filter_id not in item["id_hex"].lower().replace("0x", "") and filter_id != str(item["can_id"]):
            continue
        if filter_byte is not None and str(filter_byte) != "" and int(item["byte"]) != int(filter_byte):
            continue
        if filter_bit is not None and str(filter_bit) != "":
            if item["type"] != "bit" or int(item["bit"]) != int(filter_bit):
                continue
        if item["correlation"] < min_corr:
            continue
        if hide_counters and item.get("counter_suspect"):
            continue
        if hide_wakeup and item.get("wakeup"):
            continue
        if stable_only and item.get("changes", 0) > 0:
            continue
        result.append(item)

    result.sort(key=lambda item: (item["correlation"], item["pairs_consistent"], -item["changes"]), reverse=True)
    if hide_wakeup:
        wakeup_ids = []
    return {
        "pairs": pairs,
        "candidates": result,
        "wakeup_ids": wakeup_ids,
        "filters": filters,
        "message": "" if result else "Keine Kandidaten mit den gewaehlten Filtern.",
    }


def timeline(raw_path: Path, events_path: Path, label_a: str, label_b: str,
             can_id: int, extended: bool, byte: int, bit: int,
             before_s: float = DEFAULT_BEFORE_S, after_s: float = DEFAULT_AFTER_S,
             max_gap_s: float = DEFAULT_MAX_GAP_S, limit: int = 1200) -> dict:
    events = load_events(events_path)
    pairs = pair_events(events, label_a, label_b, before_s, after_s, max_gap_s)
    points = []
    if not pairs:
        return {"pairs": [], "points": [], "message": "Keine passenden A/B-Marker gefunden."}
    windows = []
    for pair in pairs:
        windows.append((pair["chart_start"] and parse_iso(pair["chart_start"]), pair["a_epoch_end"], pair["index"], "A"))
        windows.append((pair["b_epoch_start"], pair["b_epoch_end"], pair["index"], "B"))
    for frame in _iter_frames(raw_path):
        stamp = parse_iso(frame.get("received_iso"))
        if stamp is None:
            continue
        try:
            frame_can_id, frame_extended = frame_id(frame)
        except ValueError:
            continue
        if frame_can_id != can_id or frame_extended != extended:
            continue
        for start, end, index, state in windows:
            if start is not None and start <= stamp <= end:
                payload = data_bytes(frame)
                if byte >= len(payload):
                    continue
                points.append({
                    "pair": index,
                    "state": state,
                    "timestamp": frame.get("received_iso", ""),
                    "value": (payload[byte] >> bit) & 1,
                })
                break
    if len(points) > limit:
        step = max(1, (len(points) + limit - 1) // limit)
        points = points[::step]
    return {"pairs": pairs, "points": points, "message": ""}
