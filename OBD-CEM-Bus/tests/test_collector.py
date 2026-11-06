import csv
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import volvo_can_collector as collector


class CollectorTests(unittest.TestCase):
    def test_parse_valid_frame(self):
        line = (
            '{"seq":7,"timestamp_us":123456,"id":466,"id_hex":"0x01D2",'
            '"extended":false,"dlc":8,"data":"0102030405060708","demo":false}'
        )
        frame = collector.parse_frame(line)
        self.assertIsNotNone(frame)
        self.assertEqual(frame["seq"], 7)
        self.assertEqual(frame["id"], 466)

    def test_parse_invalid_json_and_missing_fields(self):
        self.assertIsNone(collector.parse_frame("kein json"))
        self.assertIsNone(collector.parse_frame('{"seq":1}'))
        self.assertIsNone(collector.parse_frame("# kommentar"))

    def test_frame_row_standard(self):
        frame = {
            "seq": 1,
            "timestamp_us": 100,
            "id": 0x1A0,
            "extended": False,
            "dlc": 2,
            "data": "0102000000000000",
            "demo": True,
        }
        row = collector.frame_row(frame)
        self.assertEqual(row[0], 1)
        self.assertEqual(row[1], 100)
        self.assertEqual(row[2], "0x1A0")
        self.assertEqual(row[3], 0x1A0)
        self.assertEqual(row[4], 0)
        self.assertEqual(row[5], 2)
        self.assertEqual(row[6], "0102000000000000")
        self.assertEqual(row[7], 1)

    def test_collector_writes_csv(self):
        lines = [
            '{"seq":1,"timestamp_us":1000,"id":416,"id_hex":"0x1A0","extended":false,"dlc":2,"data":"0102000000000000","demo":true}',
            '{"seq":2,"timestamp_us":2000,"id":416,"id_hex":"0x1A0","extended":false,"dlc":2,"data":"0302000000000000","demo":true}',
            '{"seq":3,"timestamp_us":3000,"id":992,"id_hex":"0x3E0","extended":false,"dlc":2,"data":"1033000000000000","demo":true}',
        ]
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def serve():
            connection, _ = server.accept()
            connection.sendall(("\n".join(lines) + "\n").encode("utf-8"))
            connection.close()
            server.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test.csv"
            result = collector.run("127.0.0.1", port, output, quiet=True, max_frames=3)
            self.assertEqual(result, 0)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0][0], "seq")
            self.assertEqual(rows[1][2], "0x1A0")
            self.assertEqual(rows[3][2], "0x3E0")
        thread.join(timeout=2)

    def test_frame_row_extended(self):
        frame = {
            "seq": 2,
            "timestamp_us": 200,
            "id": 0x1ABCDEF0,
            "extended": True,
            "dlc": 1,
            "data": "FF00000000000000",
            "demo": False,
        }
        row = collector.frame_row(frame)
        self.assertEqual(row[2], "0x1ABCDEF0")
        self.assertEqual(row[4], 1)
        self.assertEqual(row[7], 0)


if __name__ == "__main__":
    unittest.main()
