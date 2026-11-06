import json
import sys
import tempfile
import time
import unittest.mock
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import local_can_diagnostics as diagnostics
from local_can_diagnostics import DiagnosticsApp, Handler, LocalServer


def make_frame(data_hex="0100000000000000", can_id=0x1A0, demo=True, timestamp_us=1000):
    return {
        "seq": 1,
        "timestamp_us": timestamp_us,
        "id": can_id,
        "extended": False,
        "dlc": 8,
        "data": data_hex,
        "demo": demo,
        "received_iso": "2026-11-03T20:00:00.000Z",
    }


class LocalServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = DiagnosticsApp(self.root / "config", self.root / "out", demo=True)
        self.server = LocalServer(("127.0.0.1", 0), Handler, self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.app.shutdown()
        self.temp.cleanup()

    def request(self, path, method="GET", payload=None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type:
                return response.status, json.loads(body)
            return response.status, body

    def test_static_ui(self):
        status, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Volvo CAN Signalerkennung", body)
        status, css = self.request("/style.css")
        self.assertEqual(status, 200)
        status, js = self.request("/app.js")
        self.assertEqual(status, 200)

    def test_demo_status_and_signals(self):
        self.app.ingest(make_frame())
        status, data = self.request("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(data["source"], "demo")
        self.assertEqual(data["counters"]["frames_received"], 1)
        status, signals = self.request("/api/signals")
        self.assertEqual(status, 200)
        bus = next(signal for signal in signals["signals"] if signal["id"] == "can_bus_active")
        self.assertEqual(bus["led"], "green")
        reverse = next(signal for signal in signals["signals"] if signal["id"] == "reverse_gear")
        self.assertEqual(reverse["state_text"], "UNBEKANNT")

    def test_live_monitor_filters_and_rates(self):
        self.app.ingest(make_frame(can_id=0x1A0))
        self.app.ingest(make_frame(can_id=0x2C0, data_hex="0200000000000000"))
        self.app.ingest(dict(make_frame(can_id=0x18DAF110, demo=False), extended=True))
        status, data = self.request("/api/monitor?since=0&limit=10&type=all")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["frames"]), 3)
        self.assertEqual(data["latest_seq"], 3)
        self.assertGreater(data["total_rate"], 0)
        self.assertEqual(data["unique_ids"], 3)

        status, filtered = self.request("/api/monitor?since=0&limit=10&id=1A0&type=std")
        self.assertEqual(status, 200)
        self.assertEqual(len(filtered["frames"]), 1)
        self.assertFalse(filtered["frames"][0]["extended"])

        status, extended = self.request("/api/monitor?since=0&limit=10&type=ext")
        self.assertEqual(status, 200)
        self.assertEqual(len(extended["frames"]), 1)
        self.assertTrue(extended["frames"][0]["extended"])

        status, incremental = self.request(f"/api/monitor?since={data['latest_seq']}&limit=10")
        self.assertEqual(status, 200)
        self.assertEqual(incremental["frames"], [])

    def test_editor_measurement_event_and_export(self):
        _, signals = self.request("/api/signals")
        reverse = next(signal for signal in signals["signals"] if signal["id"] == "reverse_gear")
        payload = dict(reverse)
        payload.update({"can_id": "0x1A0", "byte": 0, "bit_mask": "0x1", "compare_value": 1})
        status, saved = self.request("/api/signals", "POST", payload)
        self.assertEqual(status, 200)
        self.assertEqual(saved["status"], "candidate")

        status, started = self.request("/api/measurement/start", "POST", {"name": "testmessung"})
        self.assertEqual(status, 200)
        self.app.ingest(make_frame())
        status, stopped = self.request("/api/measurement/stop", "POST", {})
        self.assertEqual(status, 200)
        self.assertTrue(Path(stopped["file"]).exists())

        status, event = self.request("/api/event/mark", "POST", {"label": "Rueckwaertsgang EIN"})
        self.assertEqual(status, 200)
        status, events = self.request("/api/events?since=0")
        self.assertTrue(any(item["kind"] == "user" for item in events["events"]))

        status, listing = self.request("/api/export/list")
        self.assertEqual(status, 200)
        self.assertTrue(any(file["name"].endswith(".csv") for file in listing["files"]))
        status, csv_body = self.request("/api/export/session?format=csv")
        self.assertEqual(status, 200)
        self.assertIn(b"seq,timestamp_us,can_id", csv_body)
        status, json_body = self.request("/api/export/session?format=json")
        self.assertEqual(status, 200)
        self.assertIsInstance(json_body, list)

    def test_assistant_http_flow_and_bind(self):
        self.app.assistant.duration = 0.2
        status, started = self.request("/api/assistant/start", "POST", {"action_label": "Test EIN"})
        self.assertEqual(status, 200)
        self.assertEqual(started["phase"], "baseline")
        for index in range(5):
            self.app.ingest(make_frame("0000000000000000", timestamp_us=index * 1000))
        time.sleep(0.3)
        status, marked = self.request("/api/assistant/mark_action", "POST", {"action_label": "Test EIN"})
        self.assertEqual(status, 200)
        self.assertEqual(marked["phase"], "action1")
        for index in range(5):
            self.app.ingest(make_frame("0100000000000000", timestamp_us=2000 + index * 1000))
        time.sleep(0.3)
        status, marked_off = self.request("/api/assistant/mark_action", "POST", {"action_label": "Test EIN"})
        self.assertEqual(status, 200)
        self.assertEqual(marked_off["phase"], "recovery")
        for index in range(5):
            self.app.ingest(make_frame("0000000000000000", timestamp_us=4000 + index * 1000))
        time.sleep(0.3)
        status, marked_again = self.request("/api/assistant/mark_action", "POST", {"action_label": "Test EIN"})
        self.assertEqual(status, 200)
        self.assertEqual(marked_again["phase"], "action2")
        for index in range(5):
            self.app.ingest(make_frame("0100000000000000", timestamp_us=6000 + index * 1000))
        time.sleep(0.3)
        status, evaluated = self.request("/api/assistant/evaluate", "POST", {})
        self.assertEqual(status, 200)
        self.assertTrue(any(candidate["byte"] == 0 and candidate["bit"] == 0 for candidate in evaluated["candidates"]))
        index = next(index for index, candidate in enumerate(evaluated["candidates"]) if candidate["bit"] == 0)
        status, signal = self.request("/api/assistant/bind", "POST", {"signal_id": "reverse_gear", "candidate_index": index})
        self.assertEqual(status, 200)
        self.assertEqual(signal["status"], "candidate")
        self.assertGreaterEqual(len(signal["evidence"]), 1)

    def test_demo_toggle_and_connection_counters(self):
        _, before = self.request("/api/status")
        self.assertFalse(before["demo_flag"])
        _, toggled = self.request("/api/demo/toggle", "POST", {})
        self.assertTrue(toggled["demo_flag"])
        self.app.on_connection(True, "COMX")
        self.app.on_connection(False, "COMX", "Kabel getrennt")
        _, status = self.request("/api/status")
        self.assertEqual(status["counters"]["serial_reconnects"], 1)
        self.assertFalse(status["connected"])

    def test_serial_disconnect_is_counted(self):
        class FakeSerial:
            def __init__(self):
                self.sent = False
            def read(self, size=4096):
                if not self.sent:
                    self.sent = True
                    return (b'{"type":"can","seq":1,"timestamp_us":1000,"id":416,'
                            b'"id_hex":"0x1A0","extended":false,"dlc":2,'
                            b'"data":"0102000000000000","demo":false}\n')
                raise diagnostics.serial.SerialException("simuliert getrennt")
            def close(self):
                pass

        app = DiagnosticsApp(self.root / "config3", self.root / "out3", demo=False, serial_port="FAKE")
        with unittest.mock.patch.object(diagnostics, "open_serial", lambda port, baud: FakeSerial()):
            app.start()
            time.sleep(0.4)
            status = app.status()
            app.stop_event.set()
            app.thread.join(timeout=3)
            app.shutdown()
        self.assertGreaterEqual(status["counters"]["serial_reconnects"], 1)
        self.assertGreaterEqual(status["counters"]["frames_received"], 0)

    def test_demo_frame_rejected_in_serial_mode(self):
        app = DiagnosticsApp(self.root / "config2", self.root / "out2", demo=False)
        app.ingest(make_frame(demo=True))
        status = app.status()
        self.assertEqual(status["counters"]["frames_received"], 0)
        self.assertEqual(status["counters"]["rejected_demo_frames"], 1)
        app.shutdown()


if __name__ == "__main__":
    unittest.main()
