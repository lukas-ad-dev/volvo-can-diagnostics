import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

try:
    import pty
    import tty
except ImportError:  # Windows: PTY-Simulation nicht verfuegbar
    pty = None
    tty = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import usb_can_logger as logger


class UsbLoggerTests(unittest.TestCase):
    def test_parse_can_line(self):
        line = (
            '{"type":"can","seq":7,"timestamp_us":1000,"id":416,'
            '"id_hex":"0x1A0","extended":false,"dlc":2,'
            '"data":"0102000000000000","demo":false}'
        )
        kind, payload = logger.parse_line(line)
        self.assertEqual(kind, "can")
        self.assertEqual(payload["seq"], 7)

    def test_parse_diag_and_raw(self):
        kind, payload = logger.parse_line("# [USB-STATS] tx=1")
        self.assertEqual(kind, "diag")
        kind, payload = logger.parse_line("boot message")
        self.assertEqual(kind, "raw")

    def test_frame_row(self):
        frame = {
            "seq": 1,
            "timestamp_us": 100,
            "id": 0x1A0,
            "extended": False,
            "dlc": 2,
            "data": "0102",
            "demo": True,
        }
        row = logger.frame_row(frame, "test")
        self.assertEqual(row[0], "test")
        self.assertEqual(row[3], "0x1A0")
        self.assertEqual(row[7], "0102000000000000")
        self.assertEqual(row[8], 1)

    def test_scenarios(self):
        self.assertEqual(logger.scenario_name("5"), "05_rueckwaertsgang")
        self.assertEqual(logger.scenario_name("kamera an"), "kamera_an")

    @unittest.skipUnless(os.name == "posix" and pty is not None and tty is not None,
                         "PTY nur unter Unix")
    def test_logger_receives_simulated_serial_data(self):
        master, slave = pty.openpty()
        tty.setraw(slave)
        port = os.ttyname(slave)
        with tempfile.TemporaryDirectory() as directory:
            env = os.environ.copy()
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "tools" / "usb_can_logger.py"),
                    "--port",
                    port,
                    "--output-dir",
                    directory,
                    "--auto-measurement",
                    "1",
                    "--max-frames",
                    "3",
                    "--headless",
                    "--quiet",
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            time.sleep(0.6)
            lines = [
                '{"type":"can","seq":1,"timestamp_us":1000,"id":416,"id_hex":"0x1A0","extended":false,"dlc":2,"data":"0102000000000000","demo":false}',
                '{"type":"can","seq":2,"timestamp_us":2000,"id":416,"id_hex":"0x1A0","extended":false,"dlc":2,"data":"0302000000000000","demo":false}',
                '# [USB-STATS] tx=2 dropped=0 errors=0',
                '{"type":"can","seq":3,"timestamp_us":3000,"id":992,"id_hex":"0x3E0","extended":false,"dlc":2,"data":"1033000000000000","demo":false}',
            ]
            try:
                os.write(master, ("\n".join(lines) + "\n").encode("utf-8"))
            except OSError:
                pass
            output, _ = process.communicate(timeout=12)
            self.assertEqual(process.returncode, 0, output)
            files = sorted(Path(directory).glob("*.csv"))
            measurement_files = [path for path in files if not path.name.startswith("session_")]
            self.assertEqual(len(measurement_files), 1, [p.name for p in files])
            rows = measurement_files[0].read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(rows), 4)
            self.assertIn("01_fahrzeug_verriegelt", rows[1])
            events = list(Path(directory).glob("*_events.log"))
            self.assertEqual(len(events), 1)
            self.assertIn("USB-STATS", events[0].read_text(encoding="utf-8"))
        os.close(master)
        os.close(slave)


if __name__ == "__main__":
    unittest.main()
