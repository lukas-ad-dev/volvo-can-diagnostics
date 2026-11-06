#!/usr/bin/env python3
"""Signal-Engine fuer die lokale Volvo-CAN-Diagnose.

Reine Python-Logik ohne CAN-Sendezugriff. Definiert Signalkacheln,
bewertet Bit-/Byte-/Mehrbyte-Signale, fuehrt den A/B-Pruefablauf aus und
verwaltet den Vertrauensstatus inklusive Bestaetigungsschutz.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

STATUSES = ("unknown", "candidate", "testing", "confirmed", "rejected")
LED_COLORS = ("green", "gray", "yellow", "red")
DEFAULT_TIMEOUT_MS = 2000


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def parse_can_id(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    try:
        return int(text, 0)
    except ValueError:
        return None


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "ext", "extended"}


def normalize_data(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value[:8]).hex().upper().ljust(16, "0")
    text = re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()
    return text.ljust(16, "0")[:16]


def frame_id(frame: dict) -> Tuple[int, bool]:
    can_id = parse_can_id(frame.get("id", frame.get("can_id")))
    if can_id is None:
        raise ValueError("Frame ohne CAN-ID")
    return can_id, parse_bool(frame.get("extended", False))


def default_signal(signal_id: str, name: str, kind: str, unit: str = "") -> dict:
    return {
        "id": signal_id,
        "name": name,
        "kind": kind,
        "unit": unit,
        "status": "unknown",
        "can_id": None,
        "extended": False,
        "dlc": 8,
        "byte": None,
        "length": 1,
        "bit_mask": 1,
        "compare_value": 1 if kind == "bool" else None,
        "invert": False,
        "timeout_ms": DEFAULT_TIMEOUT_MS,
        "endianness": "little",
        "value_min": None,
        "value_max": None,
        "factor": 1.0,
        "offset": 0.0,
        "notes": "",
        "source": "manual",
        "measurements": [],
        "evidence": [],
        "confirmed_at": None,
        "confirmed_note": "",
    }


def default_signals() -> List[dict]:
    specs = [
        ("reverse_gear", "Fahrstufe R", "bool", ""),
        ("gear_n", "Fahrstufe N", "bool", ""),
        ("gear_d", "Fahrstufe D", "bool", ""),
        ("gear_p", "Fahrstufe P", "bool", ""),
        ("parking_brake", "Parkbremse", "bool", ""),
        ("foot_brake", "Fußbremse", "bool", ""),
        ("speed", "Geschwindigkeit", "value", "km/h"),
        ("low_beam", "Abblendlicht", "bool", ""),
        ("high_beam", "Fernlicht", "bool", ""),
        ("parking_light", "Standlicht", "bool", ""),
        ("park_camera", "Parkkamera aktiv", "bool", ""),
        ("rear_camera", "Rückfahrkamera aktiv", "bool", ""),
        ("park_sensors", "Parksensoren aktiv", "bool", ""),
        ("doors", "Türen offen", "bool", ""),
        ("unlocked", "Fahrzeug entriegelt", "bool", ""),
        ("locked", "Fahrzeug von außen verriegelt", "bool", ""),
        ("ignition", "Zündungsstatus", "bool", ""),
        ("comfort_radio", "Komfortbetrieb / Radio aktiv", "bool", ""),
        ("vehicle_sleep", "Fahrzeug-Ruhezustand", "bool", ""),
        ("can_bus_active", "CAN-Bus aktiv", "bus", ""),
    ]
    signals = [default_signal(*spec) for spec in specs]
    for signal in signals:
        if signal["id"] == "speed":
            signal["value_min"] = 0
            signal["value_max"] = 300
            signal["factor"] = 1.0
            signal["offset"] = 0.0
        if signal["id"] == "can_bus_active":
            signal["status"] = "confirmed"
            signal["notes"] = "Direkt aus aktueller Frame-Aktivitaet abgeleitet, kein fahrzeugspezifischer Decoder."
            signal["timeout_ms"] = 1500
            signal["source"] = "system"
    return signals


def validate_definition(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Definition muss ein JSON-Objekt sein")
    signal_id = str(payload.get("id") or "").strip()
    if not signal_id:
        raise ValueError("Signal-ID fehlt")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Name fehlt")
    kind = str(payload.get("kind") or "bool")
    if kind not in {"bool", "value", "bus"}:
        raise ValueError("kind muss bool, value oder bus sein")
    definition = {
        "id": signal_id,
        "name": name,
        "kind": kind,
        "unit": str(payload.get("unit") or ""),
        "status": str(payload.get("status") or "unknown"),
        "can_id": parse_can_id(payload.get("can_id")),
        "extended": parse_bool(payload.get("extended", False)),
        "dlc": int(payload.get("dlc") or 8),
        "byte": None if payload.get("byte") in (None, "") else int(payload.get("byte")),
        "length": int(payload.get("length") or 1),
        "bit_mask": int(str(payload.get("bit_mask") or "1"), 0),
        "compare_value": None
        if payload.get("compare_value") in (None, "")
        else int(str(payload.get("compare_value")), 0),
        "invert": parse_bool(payload.get("invert", False)),
        "timeout_ms": int(payload.get("timeout_ms") or DEFAULT_TIMEOUT_MS),
        "endianness": str(payload.get("endianness") or "little"),
        "value_min": None if payload.get("value_min") in (None, "") else float(payload["value_min"]),
        "value_max": None if payload.get("value_max") in (None, "") else float(payload["value_max"]),
        "factor": float(payload.get("factor") if payload.get("factor") not in (None, "") else 1.0),
        "offset": float(payload.get("offset") if payload.get("offset") not in (None, "") else 0.0),
        "notes": str(payload.get("notes") or ""),
        "source": str(payload.get("source") or "manual"),
        "measurements": list(payload.get("measurements") or []),
        "evidence": list(payload.get("evidence") or []),
        "confirmed_at": payload.get("confirmed_at"),
        "confirmed_note": str(payload.get("confirmed_note") or ""),
    }
    if definition["status"] not in STATUSES:
        definition["status"] = "unknown"
    if definition["can_id"] is not None:
        if definition["can_id"] < 0:
            raise ValueError("CAN-ID darf nicht negativ sein")
        max_id = 0x1FFFFFFF if definition["extended"] else 0x7FF
        if definition["can_id"] > max_id:
            raise ValueError("CAN-ID passt nicht zum Frame-Typ")
        if definition["byte"] is None:
            raise ValueError("Byteposition fehlt")
        if not 0 <= definition["byte"] <= 7:
            raise ValueError("Byteposition muss 0..7 sein")
        if not 1 <= definition["length"] <= 8:
            raise ValueError("Laenge muss 1..8 sein")
        if definition["byte"] + definition["length"] > 8:
            raise ValueError("Byteposition plus Laenge liegt ausserhalb von 8 Bytes")
        if definition["dlc"] < definition["byte"] + definition["length"]:
            raise ValueError("DLC ist kleiner als Byteposition plus Laenge")
        if not 1 <= definition["bit_mask"] < (1 << (8 * definition["length"])):
            raise ValueError("Bitmaske passt nicht zur Laenge")
        if definition["compare_value"] is not None and definition["compare_value"] < 0:
            raise ValueError("Vergleichswert darf nicht negativ sein")
        if definition["endianness"] not in {"little", "big"}:
            raise ValueError("endianness muss little oder big sein")
    if not 100 <= definition["timeout_ms"] <= 60000:
        raise ValueError("Timeout muss 100..60000 ms sein")
    if definition["value_min"] is not None and definition["value_max"] is not None:
        if definition["value_min"] > definition["value_max"]:
            raise ValueError("value_min ist groesser als value_max")
    if definition["factor"] == 0:
        raise ValueError("Faktor darf nicht 0 sein")
    return definition


class SignalStore:
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.signals_path = self.config_dir / "signals.json"
        self.confirmed_path = self.config_dir / "confirmed_signals.json"
        self.generated_dir = self.config_dir / "generated"
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.generated_path = self.generated_dir / "esp32_signals.json"
        self.references_path = self.config_dir / "reference_ids.json"
        self.signals: List[dict] = []
        self.load()

    def load(self) -> None:
        if self.signals_path.exists():
            try:
                payload = json.loads(self.signals_path.read_text(encoding="utf-8"))
                loaded = payload.get("signals", payload) if isinstance(payload, dict) else payload
                self.signals = [validate_definition(item) for item in loaded]
            except Exception:
                self.signals = default_signals()
        else:
            self.signals = default_signals()
        known = {signal["id"] for signal in self.signals}
        for signal in default_signals():
            if signal["id"] not in known:
                self.signals.append(signal)
        self.save()

    def save(self) -> None:
        payload = {
            "version": 1,
            "updated": utc_now_iso(),
            "signals": self.signals,
        }
        tmp = self.signals_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.signals_path)

    def get(self, signal_id: str) -> Optional[dict]:
        return next((signal for signal in self.signals if signal["id"] == signal_id), None)

    def upsert(self, payload: dict) -> dict:
        candidate = validate_definition(payload)
        existing = self.get(candidate["id"])
        if existing is not None:
            definition_fields = (
                "can_id", "extended", "dlc", "byte", "length", "bit_mask",
                "compare_value", "invert", "timeout_ms", "endianness",
                "value_min", "value_max", "factor", "offset", "kind",
            )
            changed = any(existing.get(field) != candidate.get(field) for field in definition_fields)
            candidate["measurements"] = sorted(set(existing.get("measurements", []) + candidate.get("measurements", [])))
            if existing.get("kind") == "bus":
                candidate["status"] = existing.get("status", "confirmed")
                candidate["evidence"] = existing.get("evidence", [])
                candidate["confirmed_at"] = existing.get("confirmed_at")
                candidate["confirmed_note"] = existing.get("confirmed_note", "")
            elif not changed:
                candidate["status"] = existing.get("status", "unknown")
                candidate["evidence"] = existing.get("evidence", [])
                candidate["confirmed_at"] = existing.get("confirmed_at")
                candidate["confirmed_note"] = existing.get("confirmed_note", "")
                if candidate["status"] == "unknown" and candidate.get("can_id") is not None:
                    candidate["status"] = "candidate"
            else:
                # Eine geaenderte Definition entwertet alte Evidenz und Bestaetigung.
                candidate["evidence"] = []
                candidate["confirmed_at"] = None
                candidate["confirmed_note"] = ""
                candidate["status"] = "candidate" if candidate.get("can_id") is not None else "unknown"
            index = self.signals.index(existing)
            self.signals[index] = candidate
        else:
            if candidate.get("kind") == "bus":
                candidate["status"] = "confirmed"
            elif candidate.get("can_id") is not None:
                candidate["status"] = "candidate"
            else:
                candidate["status"] = "unknown"
            self.signals.append(candidate)
        self.save()
        self.save_confirmed()
        return candidate

    def set_status(self, signal_id: str, status: str) -> dict:
        if status not in {"unknown", "candidate", "testing", "rejected"}:
            raise ValueError("Dieser Status darf nur ueber die Bestaetigung gesetzt werden")
        signal = self.get(signal_id)
        if signal is None:
            raise ValueError("Signal nicht gefunden")
        signal["status"] = status
        if status != "confirmed":
            signal["confirmed_at"] = None
            signal["confirmed_note"] = ""
        self.save()
        self.save_confirmed()
        return signal

    def add_measurement(self, signal_id: str, name: str) -> None:
        if not name:
            return
        signal = self.get(signal_id)
        if signal is None:
            return
        if name not in signal["measurements"]:
            signal["measurements"].append(name)
            signal["measurements"] = signal["measurements"][-30:]
            self.save()

    def confirm(self, signal_id: str, note: str, checklist: bool) -> dict:
        signal = self.get(signal_id)
        if signal is None:
            raise ValueError("Signal nicht gefunden")
        if signal.get("status") not in {"candidate", "testing"}:
            raise ValueError("Nur Kandidaten oder Signale in Pruefung koennen bestaetigt werden")
        evidence = [entry for entry in signal.get("evidence", []) if not entry.get("demo")]
        run_ids = {entry.get("run_id") for entry in evidence if entry.get("run_id")}
        action_labels = {str(entry.get("action_label", "")).strip() for entry in evidence}
        action_labels.discard("")
        candidate_keys = {
            (entry.get("can_id"), entry.get("extended"), entry.get("byte"), entry.get("bit"))
            for entry in evidence
        }
        if len(candidate_keys) > 1:
            raise ValueError("Die Evidenz bezieht sich auf unterschiedliche Kandidaten")
        if len(run_ids) < 3:
            raise ValueError("Bestaetigung braucht mindestens 3 unabhaengige Pruefablaeufe")
        if len(action_labels) < 2:
            raise ValueError("Bestaetigung braucht mindestens zwei unterschiedliche Aktionen (z. B. EIN/AUS)")
        if not checklist:
            raise ValueError("Die praktische Pruef-Checkliste muss bestaetigt werden")
        if not note.strip():
            raise ValueError("Eine Bestaetigungsnotiz ist erforderlich")
        signal["status"] = "confirmed"
        signal["confirmed_at"] = utc_now_iso()
        signal["confirmed_note"] = note.strip()
        self.save()
        self.save_confirmed()
        return signal

    def apply_candidate(self, signal_id: str, candidate: dict, run_id: str,
                        action_label: str, measurement: str = "", demo: bool = False) -> dict:
        signal = self.get(signal_id)
        if signal is None:
            raise ValueError("Signal nicht gefunden")
        if signal.get("kind") == "bus":
            raise ValueError("Der CAN-Bus-Status kann nicht als Kandidat gebunden werden")
        updated = dict(signal)
        updated.update(
            {
                "kind": "bool",
                "can_id": int(candidate["can_id"]),
                "extended": bool(candidate.get("extended")),
                "byte": int(candidate["byte"]),
                "length": 1,
                "bit_mask": 1 << int(candidate["bit"]),
                "compare_value": 1,
                "invert": False,
                "source": "pruefablauf",
                "status": "candidate",
                "confirmed_at": None,
                "confirmed_note": "",
            }
        )
        old_key = (signal.get("can_id"), signal.get("extended"), signal.get("byte"),
                   signal.get("bit_mask"))
        new_key = (updated["can_id"], updated["extended"], updated["byte"], updated["bit_mask"])
        evidence = list(signal.get("evidence", [])) if old_key == new_key else []
        evidence.append(
            {
                "run_id": run_id,
                "action_label": action_label,
                "timestamp": utc_now_iso(),
                "can_id": updated["can_id"],
                "extended": updated["extended"],
                "byte": updated["byte"],
                "bit": int(candidate["bit"]),
                "a_value": candidate.get("a_value"),
                "b_value": candidate.get("b_value"),
                "warnings": candidate.get("warnings", []),
                "score": candidate.get("score"),
                "cycles": candidate.get("cycles", 1),
                "cycle_a_values": candidate.get("cycle_a_values"),
                "cycle_b_values": candidate.get("cycle_b_values"),
                "demo": bool(demo or candidate.get("demo")),
                "measurement": measurement,
            }
        )
        updated["evidence"] = evidence
        if measurement and measurement not in updated.get("measurements", []):
            updated["measurements"] = (updated.get("measurements", []) + [measurement])[-30:]
        updated["status"] = "testing" if len([e for e in evidence if not e.get("demo")]) >= 2 else "candidate"
        validated = validate_definition(updated)
        index = self.signals.index(signal)
        self.signals[index] = validated
        self.save()
        self.save_confirmed()
        return validated

    def save_confirmed(self) -> None:
        confirmed = [signal for signal in self.signals if signal.get("status") == "confirmed"]
        payload = {
            "version": 1,
            "updated": utc_now_iso(),
            "note": "Nur praktisch mehrfach bestaetigte Signale. Keine Hypothesen.",
            "signals": confirmed,
        }
        tmp = self.confirmed_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.confirmed_path)

        generated = []
        for signal in confirmed:
            if signal.get("kind") == "bus":
                continue
            generated.append(
                {
                    "id": signal["id"],
                    "name": signal["name"],
                    "kind": signal["kind"],
                    "can_id": signal.get("can_id"),
                    "extended": signal.get("extended", False),
                    "dlc": signal.get("dlc", 8),
                    "byte": signal.get("byte"),
                    "length": signal.get("length", 1),
                    "endianness": signal.get("endianness", "little"),
                    "bit_mask": signal.get("bit_mask"),
                    "compare_value": signal.get("compare_value"),
                    "invert": signal.get("invert", False),
                    "factor": signal.get("factor", 1.0),
                    "offset": signal.get("offset", 0.0),
                    "value_min": signal.get("value_min"),
                    "value_max": signal.get("value_max"),
                    "timeout_ms": signal.get("timeout_ms", DEFAULT_TIMEOUT_MS),
                    "unit": signal.get("unit", ""),
                    "confirmed_at": signal.get("confirmed_at"),
                }
            )
        generated_payload = {
            "version": 1,
            "generated": utc_now_iso(),
            "note": "Nur bestaetigte Signale. Noch nicht automatisch in die Firmware geladen.",
            "signals": generated,
        }
        tmp = self.generated_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(generated_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.generated_path)

    def references(self) -> dict:
        if not self.references_path.exists():
            return {"note": "Keine Referenzdatei vorhanden.", "hypotheses": []}
        return json.loads(self.references_path.read_text(encoding="utf-8"))


def data_bytes(frame: dict) -> bytes:
    return bytes.fromhex(normalize_data(frame.get("data", "")))


def extract_reading(definition: dict, frame: dict) -> dict:
    try:
        can_id, extended = frame_id(frame)
    except ValueError:
        return {"matched": False}
    if definition.get("can_id") is None:
        return {"matched": False}
    if can_id != int(definition["can_id"]) or extended != bool(definition.get("extended")):
        return {"matched": False}
    if definition.get("kind") == "bus":
        return {"matched": True, "valid": True, "active": True, "value": 1, "raw": 1}
    byte = definition.get("byte")
    length = int(definition.get("length", 1))
    if byte is None:
        return {"matched": True, "valid": False, "error": "Byteposition fehlt"}
    dlc = int(frame.get("dlc", 0))
    if dlc < int(byte) + length:
        return {"matched": True, "valid": False, "error": "DLC zu klein"}
    raw = data_bytes(frame)
    payload = raw[int(byte):int(byte) + length]
    if definition.get("endianness") == "big":
        raw_value = int.from_bytes(payload, "big", signed=False)
    else:
        raw_value = int.from_bytes(payload, "little", signed=False)
    mask = int(definition.get("bit_mask", 1))
    masked = raw_value & mask
    if definition.get("invert"):
        masked ^= mask
    compare = definition.get("compare_value")
    if definition.get("kind") == "bool":
        active = (masked == (int(compare) & mask)) if compare is not None else (masked != 0)
        value = 1 if active else 0
        scaled = float(value)
    else:
        scaled = masked * float(definition.get("factor", 1.0)) + float(definition.get("offset", 0.0))
        minimum = definition.get("value_min")
        maximum = definition.get("value_max")
        if minimum is not None and maximum is not None:
            active = float(minimum) <= scaled <= float(maximum)
        else:
            active = masked != 0
        value = scaled
    return {
        "matched": True,
        "valid": True,
        "active": bool(active),
        "value": value,
        "raw": raw_value,
        "masked": masked,
        "scaled": scaled,
    }


def led_state(definition: dict, state: dict, now_monotonic: float) -> dict:
    status = definition.get("status", "unknown")
    kind = definition.get("kind", "bool")
    last_seen = state.get("last_seen_monotonic")
    timeout_s = max(0.1, float(definition.get("timeout_ms", DEFAULT_TIMEOUT_MS)) / 1000.0)
    age = None if last_seen is None else max(0.0, now_monotonic - last_seen)

    if kind == "bus":
        active = last_seen is not None and age is not None and age <= timeout_s
        return {
            "led": "green" if active else "red",
            "text": "AKTIV" if active else "KEINE FRAMES",
            "valid": active,
            "stale": not active,
            "unknown": False,
        }
    if definition.get("can_id") is None:
        return {"led": "yellow", "text": "UNBEKANNT", "valid": False, "stale": False, "unknown": True}
    if status == "rejected":
        return {"led": "gray", "text": "VERWORFEN", "valid": False, "stale": False, "unknown": False}
    if last_seen is None:
        return {
            "led": "yellow" if status != "confirmed" else "red",
            "text": "UNBEKANNT" if status != "confirmed" else "KEINE DATEN",
            "valid": False,
            "stale": False,
            "unknown": status != "confirmed",
        }
    if age is not None and age > timeout_s:
        return {"led": "red", "text": "VERALTET", "valid": False, "stale": True, "unknown": False}
    if state.get("invalid"):
        return {"led": "red", "text": "UNGUELTIG", "valid": False, "stale": False, "unknown": False}
    active = bool(state.get("active", False))
    if status != "confirmed":
        label = "IN PRUEFUNG" if status == "testing" else ("KANDIDAT" if status == "candidate" else "UNBEKANNT")
        return {
            "led": "yellow" if active else "gray",
            "text": f"{label} {'EIN' if active else 'AUS'} (unbestaetigt)",
            "valid": True,
            "stale": False,
            "unknown": True,
        }
    return {
        "led": "green" if active else "gray",
        "text": "EIN" if active else "AUS",
        "valid": True,
        "stale": False,
        "unknown": False,
    }


class SignalRuntime:
    def __init__(self, store: SignalStore) -> None:
        self.store = store
        self.states: Dict[str, dict] = {}
        self.rates: Dict[Tuple[int, bool], dict] = {}
        self.global_rate: dict = {"last": None, "period": 0.0}
        self.last_frame_monotonic: Optional[float] = None
        self.last_frame_iso: Optional[str] = None
        self.measurement_signals: set[str] = set()

    def _rate(self, key: Tuple[int, bool], now: float) -> float:
        entry = self.rates.get(key)
        if entry is None:
            return 0.0
        age = now - entry["last"]
        if age > 5.0:
            return 0.0
        period = entry.get("period", 0.0)
        return 1.0 / period if period > 0.00001 else 0.0

    def on_frame(self, frame: dict, now_monotonic: float, measurement: str = "") -> List[dict]:
        can_id, extended = frame_id(frame)
        key = (can_id, extended)
        rate = self.rates.get(key)
        if rate is None:
            self.rates[key] = {"last": now_monotonic, "period": 0.0}
        else:
            delta = now_monotonic - rate["last"]
            if 0 < delta < 5.0:
                rate["period"] = (rate["period"] * 0.8 + delta * 0.2) if rate["period"] > 0 else delta
            rate["last"] = now_monotonic
        previous_global = self.global_rate["last"]
        if previous_global is not None:
            delta = now_monotonic - previous_global
            if 0 < delta < 5.0:
                self.global_rate["period"] = (self.global_rate["period"] * 0.8 + delta * 0.2) if self.global_rate["period"] > 0 else delta
        self.global_rate["last"] = now_monotonic
        self.last_frame_monotonic = now_monotonic
        self.last_frame_iso = frame.get("received_iso") or utc_now_iso()
        bus_state = self.states.setdefault("can_bus_active", {})
        bus_state["last_seen_monotonic"] = now_monotonic
        bus_state["last_seen_iso"] = self.last_frame_iso
        bus_state["active"] = True
        bus_state["demo"] = bool(frame.get("demo"))
        events = []
        for definition in self.store.signals:
            if definition.get("kind") == "bus" or definition.get("can_id") is None:
                continue
            reading = extract_reading(definition, frame)
            if not reading.get("matched"):
                continue
            state = self.states.setdefault(definition["id"], {})
            previous_active = state.get("active")
            previous_led = state.get("last_led")
            state["last_seen_monotonic"] = now_monotonic
            state["last_seen_iso"] = frame.get("received_iso") or utc_now_iso()
            state["invalid"] = not reading.get("valid", False)
            state["active"] = bool(reading.get("active", False)) if reading.get("valid") else False
            state["value"] = reading.get("value")
            state["raw"] = reading.get("raw")
            state["masked"] = reading.get("masked")
            state["error"] = reading.get("error", "")
            state["demo"] = bool(frame.get("demo"))
            if measurement:
                self.measurement_signals.add(definition["id"])
                state["measurement"] = measurement
            current = led_state(definition, state, now_monotonic)
            state["last_led"] = current["led"]
            if previous_active is not None and previous_active != state["active"]:
                events.append(
                    {
                        "kind": "signal_change",
                        "signal_id": definition["id"],
                        "signal": definition["name"],
                        "from": "EIN" if previous_active else "AUS",
                        "to": "EIN" if state["active"] else "AUS",
                        "value": state.get("value"),
                        "timestamp": state.get("last_seen_iso"),
                        "measurement": measurement,
                        "demo": state.get("demo", False),
                    }
                )
            elif previous_led is not None and previous_led != current["led"]:
                events.append(
                    {
                        "kind": "signal_state",
                        "signal_id": definition["id"],
                        "signal": definition["name"],
                        "from": previous_led,
                        "to": current["led"],
                        "text": current["text"],
                        "timestamp": state.get("last_seen_iso"),
                        "measurement": measurement,
                        "demo": state.get("demo", False),
                    }
                )
        return events

    def finalize_measurement(self, name: str) -> None:
        for signal_id in sorted(self.measurement_signals):
            self.store.add_measurement(signal_id, name)
        self.measurement_signals.clear()

    def snapshot(self, now_monotonic: float) -> List[dict]:
        result = []
        for definition in self.store.signals:
            state = self.states.get(definition["id"], {})
            led = led_state(definition, state, now_monotonic)
            age = None
            if state.get("last_seen_monotonic") is not None:
                age = max(0.0, now_monotonic - state["last_seen_monotonic"])
            if definition.get("kind") == "bus":
                period = self.global_rate.get("period", 0.0)
                freq = 1.0 / period if period > 0.00001 and self.last_frame_monotonic is not None and now_monotonic - self.last_frame_monotonic < 2.0 else 0.0
                if self.last_frame_monotonic is not None:
                    age = max(0.0, now_monotonic - self.last_frame_monotonic)
                else:
                    age = None
            else:
                rate_key = (parse_can_id(definition.get("can_id")), bool(definition.get("extended")))
                freq = self._rate(rate_key, now_monotonic) if rate_key[0] is not None else 0.0
            item = dict(definition)
            item.update(
                {
                    "led": led["led"],
                    "state_text": led["text"],
                    "valid": led["valid"],
                    "stale": led["stale"],
                    "unknown": led["unknown"],
                    "age_ms": None if age is None else round(age * 1000.0, 1),
                    "last_update": state.get("last_seen_iso"),
                    "freq_hz": round(freq, 3),
                    "raw_value": state.get("raw"),
                    "masked_value": state.get("masked"),
                    "display_value": state.get("value"),
                    "active": bool(state.get("active")) if definition.get("kind") != "bus" else led["valid"],
                    "demo": bool(state.get("demo")),
                    "evidence_count": len([e for e in definition.get("evidence", []) if not e.get("demo")]),
                    "id_hex": f"0x{int(definition['can_id']):0{8 if definition.get('extended') else 3}X}"
                    if definition.get("can_id") is not None
                    else None,
                }
            )
            result.append(item)
        return result


class PhaseAccumulator:
    def __init__(self) -> None:
        self.ids: Dict[Tuple[int, bool], dict] = {}

    def add(self, frame: dict) -> None:
        can_id, extended = frame_id(frame)
        key = (can_id, extended)
        entry = self.ids.get(key)
        if entry is None:
            entry = {
                "count": 0,
                "first": None,
                "last": None,
                "last_data": normalize_data(frame.get("data", "")),
                "last_dlc": int(frame.get("dlc", 0)),
                "max_dlc": 0,
                "seen": [[[0, 0] for _ in range(8)] for _ in range(8)],
                "demo": False,
            }
            self.ids[key] = entry
        now = float(frame.get("timestamp_us", 0)) / 1_000_000.0
        entry["count"] += 1
        entry["demo"] = entry["demo"] or bool(frame.get("demo"))
        if entry["first"] is None or now < entry["first"]:
            entry["first"] = now
        if entry["last"] is None or now >= entry["last"]:
            entry["last"] = now
            entry["last_data"] = normalize_data(frame.get("data", ""))
            entry["last_dlc"] = int(frame.get("dlc", 0))
        entry["max_dlc"] = max(entry["max_dlc"], int(frame.get("dlc", 0)))
        data = data_bytes(frame)
        for byte in range(min(int(frame.get("dlc", 0)), 8)):
            for bit in range(8):
                entry["seen"][byte][bit][(data[byte] >> bit) & 1] += 1

    @staticmethod
    def _stable(entry: dict, byte: int, bit: int) -> Optional[int]:
        seen = entry["seen"][byte][bit]
        if seen[0] > 0 and seen[1] == 0:
            return 0
        if seen[1] > 0 and seen[0] == 0:
            return 1
        return None

    @staticmethod
    def _mixed_count(entry: dict) -> int:
        count = 0
        for byte in range(entry["max_dlc"]):
            for bit in range(8):
                if entry["seen"][byte][bit][0] > 0 and entry["seen"][byte][bit][1] > 0:
                    count += 1
        return count

    def compare(self, other: "PhaseAccumulator") -> dict:
        candidates = []
        new_ids = []
        missing_ids = []
        for key in sorted(set(self.ids) | set(other.ids), key=lambda item: (item[0], item[1])):
            a = self.ids.get(key)
            b = other.ids.get(key)
            id_hex = f"0x{key[0]:0{8 if key[1] else 3}X}"
            if a is None and b is not None:
                new_ids.append({"can_id": key[0], "id_hex": id_hex, "extended": key[1], "count_b": b["count"], "warnings": ["ID nur in Phase B"], "demo": b["demo"]})
                continue
            if b is None and a is not None:
                missing_ids.append({"can_id": key[0], "id_hex": id_hex, "extended": key[1], "count_a": a["count"], "warnings": ["ID nur in Phase A"], "demo": a["demo"]})
                continue
            if a is None or b is None:
                continue
            if a["count"] < 3 or b["count"] < 3:
                continue
            mixed_a = self._mixed_count(a)
            mixed_b = self._mixed_count(b)
            for byte in range(min(a["max_dlc"], b["max_dlc"])):
                for bit in range(8):
                    sa = self._stable(a, byte, bit)
                    sb = self._stable(b, byte, bit)
                    if sa is None or sb is None or sa == sb:
                        continue
                    warnings = []
                    if mixed_a or mixed_b:
                        warnings.append("andere Bits dieses Frames wechseln (Zaehler/Pruefsumme moeglich)")
                    byte_mixed = any(
                        a["seen"][byte][x][0] > 0 and a["seen"][byte][x][1] > 0
                        or b["seen"][byte][x][0] > 0 and b["seen"][byte][x][1] > 0
                        for x in range(8)
                    )
                    if byte_mixed:
                        warnings.append("Byte enthaelt wechselnde Bits")
                    if min(a["count"], b["count"]) < 5:
                        warnings.append("wenige Frames")
                    if a["demo"] or b["demo"]:
                        warnings.append("DEMO-Daten")
                    score = 100.0
                    if mixed_a or mixed_b:
                        score *= 0.55
                    if byte_mixed:
                        score *= 0.7
                    score *= min(1.0, min(a["count"], b["count"]) / 10.0)
                    candidates.append(
                        {
                            "can_id": key[0],
                            "id_hex": id_hex,
                            "extended": key[1],
                            "byte": byte,
                            "bit": bit,
                            "mask": 1 << bit,
                            "a_value": sa,
                            "b_value": sb,
                            "count_a": a["count"],
                            "count_b": b["count"],
                            "score": round(score, 1),
                            "warnings": warnings,
                            "demo": a["demo"] or b["demo"],
                        }
                    )
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return {"candidates": candidates, "new_ids": new_ids, "missing_ids": missing_ids}


class AssistantSession:
    def __init__(self, duration_seconds: float = 10.0) -> None:
        self.duration = duration_seconds
        self.reset()

    def reset(self) -> None:
        self.run_id = None
        self.phase = "idle"
        self.started_at = None
        self.phase_started_at = None
        self.action_label = ""
        self.baseline = PhaseAccumulator()
        self.action = PhaseAccumulator()
        self.candidates: List[dict] = []
        self.new_ids: List[dict] = []
        self.missing_ids: List[dict] = []

    def start(self, action_label: str = "", now: Optional[float] = None) -> dict:
        self.reset()
        self.run_id = uuid.uuid4().hex[:12]
        self.action_label = action_label.strip()
        self.phase = "baseline"
        self.started_at = now if now is not None else time.monotonic()
        self.phase_started_at = self.started_at
        return self.status(now)

    def tick(self, now: Optional[float] = None) -> None:
        now = now if now is not None else time.monotonic()
        if self.phase == "baseline" and self.phase_started_at is not None and now - self.phase_started_at >= self.duration:
            self.phase = "waiting_action"
        elif self.phase == "action" and self.phase_started_at is not None and now - self.phase_started_at >= self.duration:
            self.phase = "ready"

    def on_frame(self, frame: dict, now: Optional[float] = None) -> None:
        self.tick(now)
        if self.phase == "baseline":
            self.baseline.add(frame)
        elif self.phase == "action":
            self.action.add(frame)

    def mark_action(self, label: str = "", now: Optional[float] = None) -> dict:
        now = now if now is not None else time.monotonic()
        self.tick(now)
        if self.phase != "waiting_action":
            raise ValueError("Aktion kann erst nach der Grundzustandsphase markiert werden")
        if label.strip():
            self.action_label = label.strip()
        self.phase = "action"
        self.phase_started_at = now
        return self.status(now)

    def evaluate(self, now: Optional[float] = None) -> dict:
        now = now if now is not None else time.monotonic()
        self.tick(now)
        if self.phase != "ready":
            if self.phase == "action":
                raise ValueError("Aktionsphase ist noch nicht beendet")
            raise ValueError("Noch keine auswertbare Aktion vorhanden")
        result = self.baseline.compare(self.action)
        self.candidates = result["candidates"]
        self.new_ids = result["new_ids"]
        self.missing_ids = result["missing_ids"]
        self.phase = "evaluated"
        return self.status(now)

    def status(self, now: Optional[float] = None) -> dict:
        now = now if now is not None else time.monotonic()
        self.tick(now)
        remaining = 0.0
        if self.phase in {"baseline", "action"} and self.phase_started_at is not None:
            remaining = max(0.0, self.duration - (now - self.phase_started_at))
        return {
            "run_id": self.run_id,
            "phase": self.phase,
            "action_label": self.action_label,
            "remaining_seconds": round(remaining, 1),
            "baseline_frames": sum(entry["count"] for entry in self.baseline.ids.values()),
            "action_frames": sum(entry["count"] for entry in self.action.ids.values()),
            "baseline_ids": len(self.baseline.ids),
            "action_ids": len(self.action.ids),
            "candidates": self.candidates,
            "new_ids": self.new_ids,
            "missing_ids": self.missing_ids,
            "duration_seconds": self.duration,
            "cycles": 1,
        }
