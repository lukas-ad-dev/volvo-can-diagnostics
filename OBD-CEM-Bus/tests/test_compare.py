import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import compare_measurements as compare


HEADER = [
    "measurement",
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


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)


class CompareTests(unittest.TestCase):
    def test_changed_bits_and_new_id(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory) / "a.csv"
            b = Path(directory) / "b.csv"
            write_csv(a, [
                ["a", 1, 0, "0x1A0", 416, 0, 8, "0100000000000000", 0, "t"],
                ["a", 2, 1000000, "0x1A0", 416, 0, 8, "0100000000000000", 0, "t"],
            ])
            write_csv(b, [
                ["b", 3, 2000000, "0x1A0", 416, 0, 8, "0300000000000000", 0, "t"],
                ["b", 4, 3000000, "0x200", 512, 0, 2, "7F00000000000000", 0, "t"],
            ])
            ma = compare.load_measurement(a)
            mb = compare.load_measurement(b)
            result = compare.compare(ma, mb)
            self.assertEqual(len(result["new_ids"]), 1)
            self.assertEqual(result["new_ids"][0]["id_hex"], "0x200")
            self.assertEqual(len(result["changed"]), 1)
            changed = result["changed"][0]
            self.assertEqual(changed["id_hex"], "0x1A0")
            self.assertTrue(changed["payload_changed"])
            self.assertEqual(changed["changed_bytes"][0]["xor"], "02")
            self.assertEqual(changed["changed_bytes"][0]["bits"], [1])

    def test_demo_frames_are_skipped_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory) / "a.csv"
            b = Path(directory) / "b.csv"
            write_csv(a, [
                ["a", 1, 0, "0x1A0", 416, 0, 2, "0102000000000000", 1, "t"],
            ])
            write_csv(b, [
                ["b", 2, 0, "0x1A0", 416, 0, 2, "0102000000000000", 0, "t"],
            ])
            ma = compare.load_measurement(a)
            mb = compare.load_measurement(b)
            self.assertEqual(ma.demo_skipped, 1)
            self.assertEqual(ma.frames, 0)
            self.assertEqual(mb.frames, 1)


if __name__ == "__main__":
    unittest.main()
