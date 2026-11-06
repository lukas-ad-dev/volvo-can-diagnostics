import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import analysis_engine


BASE = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def iso(seconds):
    return (BASE + timedelta(seconds=seconds)).isoformat(timespec="milliseconds")


def write_session(directory: Path):
    raw = directory / "session_test_raw.jsonl"
    events = directory / "session_test_events.jsonl"
    with open(raw, "w", encoding="utf-8") as handle:
        for step in range(0, 80):
            t = step * 0.1
            if 0.6 <= t <= 2.4 or 4.6 <= t <= 6.4:
                bit0 = 0
            elif 2.6 <= t <= 4.4 or 6.6 <= t <= 8.4:
                bit0 = 1
            else:
                bit0 = 0
            data = "01" if bit0 else "00"
            frame = {
                "type": "frame",
                "seq": step + 1,
                "timestamp_us": int(t * 1_000_000),
                "can_id": 0x1A0,
                "extended": False,
                "dlc": 8,
                "data": data + "00000000000000",
                "received_iso": iso(t),
                "demo": False,
            }
            handle.write(json.dumps(frame) + "\n")
            counter = {
                **frame,
                "seq": 1000 + step,
                "can_id": 0x1A1,
                "data": f"{step & 0xFF:02X}" + "00000000000000",
            }
            handle.write(json.dumps(counter) + "\n")
            if bit0:
                wake = {
                    **frame,
                    "seq": 2000 + step,
                    "can_id": 0x1A2,
                    "data": "AA00000000000000",
                }
                handle.write(json.dumps(wake) + "\n")
        padding = {
            "type": "frame",
            "seq": 3000,
            "timestamp_us": 1000000,
            "can_id": 0x1A3,
            "extended": False,
            "dlc": 3,
            "data": "55AA000000000000",
            "received_iso": iso(1.0),
            "demo": False,
        }
        handle.write(json.dumps(padding) + "\n")
    with open(events, "w", encoding="utf-8") as handle:
        for marker, label in [(0.5, "Licht AUS"), (2.5, "Licht AN"), (4.5, "Licht AUS"), (6.5, "Licht AN")]:
            handle.write(json.dumps({
                "id": int(marker * 10) + 1,
                "kind": "user",
                "label": label,
                "timestamp": iso(marker),
                "measurement": "",
            }) + "\n")
    return raw, events


class AnalysisEngineTests(unittest.TestCase):
    def test_pair_events_and_bit_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, events = write_session(Path(directory))
            result = analysis_engine.analyze(raw, events, "Licht AUS", "Licht AN",
                                             before_s=2, after_s=5, max_gap_s=20)
            self.assertEqual(len(result["pairs"]), 2)
            candidates = result["candidates"]
            target = next(
                item for item in candidates
                if item["type"] == "bit" and item["can_id"] == 0x1A0
                and item["byte"] == 0 and item["bit"] == 0
            )
            self.assertEqual(target["a_value"], 0)
            self.assertEqual(target["b_value"], 1)
            self.assertGreaterEqual(target["correlation"], 90)
            self.assertGreaterEqual(target["pairs_consistent"], 2)
            self.assertTrue(any(item["id_hex"] == "0x1A2" for item in result["wakeup_ids"]))

    def test_overview_ignores_padding(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, _ = write_session(Path(directory))
            result = analysis_engine.overview(raw)
            entry = next(item for item in result["ids"] if item["can_id"] == 0x1A3)
            self.assertEqual(entry["dlc"], 3)
            self.assertTrue(entry["bytes"][3]["bits"][0]["padding"])
            self.assertEqual(entry["bytes"][0]["bits"][0]["samples"], 1)
            self.assertFalse(entry["bytes"][0]["bits"][0]["padding"])

    def test_technical_logs_are_not_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            _, events = write_session(Path(directory))
            with open(events, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "kind": "firmware_can",
                    "label": "# [CMD] CAN=ARMED",
                    "timestamp": iso(0.0),
                    "measurement": "",
                }) + "\n")
            loaded = analysis_engine.load_events(events)
            self.assertNotIn("# [CMD] CAN=ARMED", [item["label"] for item in loaded])
            self.assertEqual(len(loaded), 4)

    def test_zero_byte_and_bit_filters_are_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, events = write_session(Path(directory))
            result = analysis_engine.analyze(
                raw, events, "Licht AUS", "Licht AN", 2, 5, 20,
                filters={"byte": 0, "bit": 0, "min_correlation": 80},
            )
            self.assertTrue(result["candidates"])
            self.assertTrue(all(item["byte"] == 0 for item in result["candidates"]))
            result = analysis_engine.analyze(
                raw, events, "Licht AUS", "Licht AN", 2, 5, 20,
                filters={"byte": 0, "bit": 1, "min_correlation": 80},
            )
            self.assertFalse(result["candidates"])

    def test_timeline_contains_states(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, events = write_session(Path(directory))
            result = analysis_engine.timeline(raw, events, "Licht AUS", "Licht AN",
                                              0x1A0, False, 0, 0, before_s=2, after_s=5)
            self.assertTrue(result["points"])
            states = {point["state"] for point in result["points"]}
            self.assertEqual(states, {"A", "B"})
            self.assertTrue(any(point["value"] == 0 for point in result["points"]))
            self.assertTrue(any(point["value"] == 1 for point in result["points"]))


if __name__ == "__main__":
    unittest.main()
