import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from signal_engine import (
    AssistantSession,
    PhaseAccumulator,
    SignalRuntime,
    SignalStore,
    extract_reading,
    led_state,
    validate_definition,
)


def definition(**overrides):
    base = {
        "id": "test_signal",
        "name": "Test",
        "kind": "bool",
        "unit": "",
        "status": "confirmed",
        "can_id": "0x1A0",
        "extended": False,
        "dlc": 8,
        "byte": 0,
        "length": 1,
        "bit_mask": "0x01",
        "compare_value": 1,
        "invert": False,
        "timeout_ms": 1000,
        "endianness": "little",
        "value_min": None,
        "value_max": None,
        "factor": 1.0,
        "offset": 0.0,
        "notes": "",
        "source": "test",
        "measurements": [],
        "evidence": [],
        "confirmed_at": None,
        "confirmed_note": "",
    }
    base.update(overrides)
    return validate_definition(base)


def frame(data_hex="0100000000000000", can_id=0x1A0, extended=False, demo=False, ts=0):
    return {
        "id": can_id,
        "extended": extended,
        "dlc": 8,
        "data": data_hex,
        "demo": demo,
        "timestamp_us": ts,
        "received_iso": "2026-11-03T20:00:00.000Z",
    }


class SignalEngineTests(unittest.TestCase):
    def test_led_confirmed_states(self):
        signal = definition()
        self.assertEqual(led_state(signal, {"last_seen_monotonic": 1.0, "active": True}, 1.1)["led"], "green")
        self.assertEqual(led_state(signal, {"last_seen_monotonic": 1.0, "active": False}, 1.1)["led"], "gray")
        self.assertEqual(led_state(signal, {"last_seen_monotonic": 1.0, "active": True}, 3.0)["led"], "red")
        self.assertEqual(led_state(signal, {}, 3.0)["text"], "KEINE DATEN")

    def test_led_unknown_and_candidate(self):
        candidate = definition(status="candidate")
        self.assertEqual(led_state(candidate, {"last_seen_monotonic": 1.0, "active": True}, 1.1)["led"], "yellow")
        unassigned = definition(can_id=None, status="unknown")
        self.assertEqual(led_state(unassigned, {}, 1.0)["text"], "UNBEKANNT")

    def test_bit_mask_and_invert(self):
        signal = definition(bit_mask="0x02", compare_value=2)
        self.assertTrue(extract_reading(signal, frame("0200000000000000"))["active"])
        self.assertFalse(extract_reading(signal, frame("0100000000000000"))["active"])
        inverted = definition(bit_mask="0x02", compare_value=2, invert=True)
        self.assertFalse(extract_reading(inverted, frame("0200000000000000"))["active"])

    def test_multibyte_value_little_and_big(self):
        little = definition(kind="value", length=2, bit_mask="0xFFFF", compare_value=None,
                            value_min=0, value_max=10000, factor=1.0, offset=0.0)
        self.assertEqual(extract_reading(little, frame("3412000000000000"))["raw"], 0x1234)
        big = definition(kind="value", length=2, endianness="big", bit_mask="0xFFFF",
                         compare_value=None, value_min=0, value_max=10000)
        self.assertEqual(extract_reading(big, frame("3412000000000000"))["raw"], 0x3412)
        scaled = definition(kind="value", length=2, bit_mask="0xFFFF", compare_value=None,
                            value_min=0, value_max=300, factor=0.1, offset=0.0)
        reading = extract_reading(scaled, frame("3412000000000000"))
        self.assertAlmostEqual(reading["scaled"], 466.0)

    def test_assistant_finds_stable_bit_and_ignores_counter(self):
        assistant = AssistantSession(duration_seconds=10.0)
        assistant.start("Rueckwaertsgang EIN", now=0.0)
        for index in range(10):
            assistant.on_frame(frame("0000000000000000", ts=index * 100_000), now=index * 1.0)
        assistant.tick(now=10.1)
        self.assertEqual(assistant.phase, "waiting_action")
        assistant.mark_action("Rueckwaertsgang EIN", now=10.1)
        for index in range(10):
            data = "03" if index % 2 == 0 else "01"
            assistant.on_frame(frame(data + "00000000000000", ts=(index + 11) * 100_000), now=11.0 + index)
        assistant.tick(now=21.1)
        self.assertEqual(assistant.phase, "ready")
        result = assistant.evaluate(now=21.1)
        candidates = result["candidates"]
        self.assertTrue(any(c["byte"] == 0 and c["bit"] == 0 for c in candidates))
        self.assertFalse(any(c["byte"] == 0 and c["bit"] == 1 for c in candidates))
        target = next(c for c in candidates if c["bit"] == 0)
        self.assertIn("Byte enthaelt wechselnde Bits", target["warnings"])

    def test_assistant_requires_counter_action_and_three_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SignalStore(Path(directory))
            candidate = {
                "can_id": 0x1A0,
                "extended": False,
                "byte": 0,
                "bit": 0,
                "a_value": 0,
                "b_value": 1,
                "warnings": [],
                "score": 90,
                "demo": False,
            }
            store.apply_candidate("reverse_gear", candidate, "run1", "Rueckwaertsgang EIN")
            store.apply_candidate("reverse_gear", candidate, "run2", "Rueckwaertsgang AUS")
            with self.assertRaises(ValueError):
                store.confirm("reverse_gear", "zu frueh", True)
            store.apply_candidate("reverse_gear", candidate, "run3", "Rueckwaertsgang EIN")
            confirmed = store.confirm("reverse_gear", "Dreimal praktisch geprueft, Gegenaktion bestaetigt.", True)
            self.assertEqual(confirmed["status"], "confirmed")
            self.assertTrue((Path(directory) / "confirmed_signals.json").exists())
            generated = (Path(directory) / "generated" / "esp32_signals.json").read_text(encoding="utf-8")
            self.assertIn("reverse_gear", generated)

    def test_status_transitions_are_guarded(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SignalStore(Path(directory))
            signal = store.set_status("reverse_gear", "testing")
            self.assertEqual(signal["status"], "testing")
            with self.assertRaises(ValueError):
                store.set_status("reverse_gear", "confirmed")
            signal = store.set_status("reverse_gear", "rejected")
            self.assertEqual(signal["status"], "rejected")
            signal = store.set_status("reverse_gear", "candidate")
            self.assertEqual(signal["status"], "candidate")

    def test_demo_evidence_cannot_confirm(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SignalStore(Path(directory))
            candidate = {
                "can_id": 0x1A0, "extended": False, "byte": 0, "bit": 0,
                "a_value": 0, "b_value": 1, "warnings": [], "score": 90, "demo": True,
            }
            for index in range(3):
                store.apply_candidate("reverse_gear", candidate, f"run{index}", "EIN" if index % 2 == 0 else "AUS", demo=True)
            with self.assertRaises(ValueError):
                store.confirm("reverse_gear", "Demo", True)

    def test_runtime_repeated_transitions(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SignalStore(Path(directory))
            store.upsert({
                **store.get("reverse_gear"),
                "can_id": "0x1A0",
                "byte": 0,
                "bit_mask": "0x01",
                "compare_value": 1,
            })
            runtime = SignalRuntime(store)
            events = []
            for index in range(7):
                value = "01" if index % 2 else "00"
                events.extend(runtime.on_frame(frame(value + "00000000000000"), 1.0 + index * 0.5))
            self.assertGreaterEqual(len(events), 5)
            self.assertTrue(all(event["kind"] == "signal_change" for event in events))

    def test_runtime_snapshot_and_bus(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SignalStore(Path(directory))
            store.upsert({
                **store.get("reverse_gear"),
                "can_id": "0x1A0",
                "byte": 0,
                "bit_mask": "0x01",
                "compare_value": 1,
            })
            runtime = SignalRuntime(store)
            runtime.on_frame(frame("0000000000000000"), 1.0, "messung1")
            events = runtime.on_frame(frame("0100000000000000"), 1.1, "messung1")
            self.assertTrue(events)
            snapshot = runtime.snapshot(1.2)
            reverse = next(item for item in snapshot if item["id"] == "reverse_gear")
            self.assertEqual(reverse["led"], "yellow")
            self.assertEqual(reverse["state_text"], "KANDIDAT EIN (unbestaetigt)")
            bus = next(item for item in snapshot if item["id"] == "can_bus_active")
            self.assertEqual(bus["led"], "green")
            runtime.finalize_measurement("messung1")
            self.assertIn("messung1", store.get("reverse_gear")["measurements"])


if __name__ == "__main__":
    unittest.main()
