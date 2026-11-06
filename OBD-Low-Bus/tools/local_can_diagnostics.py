#!/usr/bin/env python3
"""Lokaler Windows-Diagnoseserver fuer Volvo CAN Control.

Startet eine nur auf 127.0.0.1 gebundene Weboberflaeche, liest den
USB-CDC-NDJSON-Stream des ESP32 und bietet Signalkacheln, Signal-Editor,
Pruefablauf, Live-Test, Zeitlinie und Exporte. Es wird ausschliesslich
gelesen; es gibt keinen CAN-Sendezpfad.
"""
from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import queue
import re
import shutil
import sys
import threading
import time
from collections import Counter, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("Fehler: pyserial ist nicht installiert.")
    print("Installation:  python -m pip install -r tools/requirements.txt")
    raise SystemExit(2)

from signal_engine import (
    AssistantSession,
    SignalRuntime,
    SignalStore,
    utc_now_iso,
)
from usb_can_logger import (
    Logger,
    SCENARIOS,
    find_esp_port,
    open_serial,
    parse_line,
    scenario_name,
)

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "local_web"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".jsonl": "application/x-ndjson; charset=utf-8",
}
USB_STATS_RE = re.compile(
    r"USB-STATS.*tx=(\d+).*dropped=(\d+).*txerr=(\d+).*diagdrop=(\d+).*queue=(\d+)/(\d+)"
)


class DiagnosticsApp:
    def __init__(self, config_dir: Path, output_dir: Path, demo: bool = False,
                 serial_port: Optional[str] = None, baud: int = 115200,
                 profile: str = "OBD-Low-Bus") -> None:
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.demo_mode = demo
        self.profile = profile
        self.source = "demo" if demo else "serial"
        self.serial_port = serial_port
        self.serial_port_locked = serial_port is not None
        self.baud = baud
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir) / ("demo" if demo else "")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.store = SignalStore(self.config_dir)
        self.runtime = SignalRuntime(self.store)
        self.assistant = AssistantSession(10.0)
        self.logger = Logger(self.output_dir, quiet=True)
        self.session_stem = self.logger.session_path.stem
        self.raw_path = self.output_dir / f"{self.session_stem}_raw.jsonl"
        self.events_path = self.output_dir / f"{self.session_stem}_events.jsonl"
        self.meta_path = self.output_dir / f"{self.session_stem}_meta.json"
        self.raw_file = self.raw_path.open("a", encoding="utf-8")
        self.events_file = self.events_path.open("a", encoding="utf-8")
        self.last_raw_flush = time.monotonic()
        self.last_meta_write = time.monotonic()

        self.started_monotonic = time.monotonic()
        self.started_iso = utc_now_iso()
        self.frames_received = 0
        self.demo_frames = 0
        self.rejected_demo_frames = 0
        self.parse_errors = 0
        self.raw_lines = 0
        self.serial_reconnects = 0
        self.connected = False
        self.last_error = ""
        self.last_frame_monotonic: Optional[float] = None
        self.last_frame_iso: Optional[str] = None
        self.measurement = ""
        self.measurement_active = False
        self.assistant_running = False
        self.demo_flag = False
        self.firmware_stats: dict = {}
        self.events: deque = deque(maxlen=2500)
        self.frames: deque = deque(maxlen=2000)
        self.monitor_seq = 0
        self.rate_samples: deque = deque(maxlen=40000)
        self.event_seq = 0
        self.thread: Optional[threading.Thread] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.processor_thread: Optional[threading.Thread] = None
        self.line_queue: Optional[queue.Queue] = None
        self.line_queue_dropped = 0
        self._meta_written = False
        self._write_meta()

    # ---------- persistence / meta ----------
    def _write_meta(self) -> None:
        meta = {
            "session": self.session_stem,
            "started": self.started_iso,
            "source": self.source,
            "serial_port": self.serial_port,
            "baud": self.baud,
            "demo_mode": self.demo_mode,
            "session_csv": str(self.logger.session_path),
            "session_events_log": str(self.logger.events_path),
            "raw_jsonl": str(self.raw_path),
            "events_jsonl": str(self.events_path),
            "counters": self._counters(),
            "firmware_stats": self.firmware_stats,
        }
        self.meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self._write_raw({"type": "meta", "event": "session_start", **meta})
        if not self._meta_written:
            self._meta_written = True

    def _write_raw(self, payload: dict) -> None:
        self.raw_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
        now = time.monotonic()
        if now - self.last_raw_flush >= 2.0:
            self.raw_file.flush()
            self.last_raw_flush = now

    def _write_event_file(self, event: dict) -> None:
        self.events_file.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.events_file.flush()

    def _counters(self) -> dict:
        return {
            "frames_received": self.frames_received,
            "demo_frames": self.demo_frames,
            "rejected_demo_frames": self.rejected_demo_frames,
            "parse_errors": self.parse_errors,
            "raw_lines": self.raw_lines,
            "serial_reconnects": self.serial_reconnects,
            "line_queue_dropped": self.line_queue_dropped,
            "line_queue_size": self.line_queue.qsize() if self.line_queue is not None else 0,
            "firmware": dict(self.firmware_stats),
        }

    def record_event(self, kind: str, **fields: Any) -> dict:
        with self.lock:
            self.event_seq += 1
            event = {
                "id": self.event_seq,
                "kind": kind,
                "timestamp": utc_now_iso(),
                "measurement": self.measurement,
                "demo": self.demo_mode,
                **fields,
            }
            self.events.append(event)
            self._write_event_file(event)
            return event

    # ---------- ingest ----------
    def ingest(self, frame: dict) -> None:
        now = time.monotonic()
        frame = dict(frame)
        frame["received_iso"] = frame.get("received_iso") or utc_now_iso()
        frame["demo"] = bool(frame.get("demo"))
        frame["timestamp_us"] = int(frame.get("timestamp_us", int((now - self.started_monotonic) * 1_000_000)))
        if self.demo_mode:
            frame["demo"] = True
        if not self.demo_mode and frame["demo"]:
            # Kein Vermischen von echten und DEMO-Daten im Serialmodus.
            with self.lock:
                self.rejected_demo_frames += 1
                self.record_event("demo_rejected", message="DEMO-Frame im Serialmodus ignoriert")
            return
        with self.lock:
            self.frames_received += 1
            if frame["demo"]:
                self.demo_frames += 1
            self.monitor_seq += 1
            frame["monitor_seq"] = self.monitor_seq
            self.rate_samples.append((now, int(frame.get("id", 0))))
            self.last_frame_monotonic = now
            self.last_frame_iso = frame["received_iso"]
            self.logger.record(frame)
            self._write_raw(
                {
                    "type": "frame",
                    "measurement": self.measurement,
                    "seq": int(frame.get("seq", 0)),
                    "timestamp_us": frame["timestamp_us"],
                    "can_id": int(frame.get("id", 0)),
                    "extended": bool(frame.get("extended")),
                    "dlc": int(frame.get("dlc", 0)),
                    "data": str(frame.get("data", "")),
                    "demo": frame["demo"],
                    "received_iso": frame["received_iso"],
                    "source": self.source,
                }
            )
            self.frames.append(frame)
            for event in self.runtime.on_frame(frame, now, self.measurement):
                self.record_event(event.pop("kind", "signal_change"), **event)
            self.assistant.on_frame(frame, now)
            self._write_meta_if_needed()

    def _write_meta_if_needed(self) -> None:
        now = time.monotonic()
        if self.frames_received % 5000 == 0 or (now - self.last_meta_write) >= 30.0:
            self.last_meta_write = now
            self._write_meta()

    def on_diag(self, message: str) -> None:
        with self.lock:
            self.logger.diagnostic(message)
            match = USB_STATS_RE.search(message)
            if match:
                self.firmware_stats = {
                    "tx": int(match.group(1)),
                    "dropped": int(match.group(2)),
                    "tx_errors": int(match.group(3)),
                    "diag_dropped": int(match.group(4)),
                    "queue_used": int(match.group(5)),
                    "queue_capacity": int(match.group(6)),
                }
                self.record_event("firmware_stats", message=message, firmware=self.firmware_stats)
            else:
                self.record_event("diag", message=message)

    def on_raw_line(self, text: str) -> None:
        with self.lock:
            self.raw_lines += 1
            if text.strip().startswith("{"):
                self.parse_errors += 1
                self.record_event("parse_error", message=text[:400])
            else:
                self.logger.diagnostic(text[:400])
                self.record_event("raw", message=text[:400])

    def on_connection(self, connected: bool, port: Optional[str], error: str = "") -> None:
        with self.lock:
            was_connected = self.connected
            self.connected = connected
            self.serial_port = port or self.serial_port
            if connected:
                self.last_error = ""
                self.record_event("connection", connected=True, port=port, message=f"USB verbunden: {port}")
            else:
                if was_connected:
                    self.serial_reconnects += 1
                self.last_error = error
                if was_connected:
                    self.record_event("connection", connected=False, port=port, message=f"USB getrennt: {error}")

    # ---------- measurement / events ----------
    def start_measurement(self, name: str) -> dict:
        with self.lock:
            if self.measurement_active:
                raise ValueError("Es laeuft bereits eine Messung")
            label = scenario_name(name.strip()) if name.strip() else "messung"
            self.logger.start_measurement(label)
            self.measurement = self.logger.measurement_name or label
            self.measurement_active = True
            self.record_event("measurement_start", name=self.measurement)
            self._write_meta()
            return {"measurement": self.measurement, "file": str(self.logger.measurement_path)}

    def stop_measurement(self) -> dict:
        with self.lock:
            if not self.measurement_active:
                raise ValueError("Es laeuft keine Messung")
            name = self.measurement
            path = self.logger.stop_measurement()
            self.runtime.finalize_measurement(name)
            self.measurement = ""
            self.measurement_active = False
            self.record_event("measurement_stop", name=name, file=str(path) if path else "")
            self._write_meta()
            return {"measurement": name, "file": str(path) if path else ""}

    def mark_event(self, label: str) -> dict:
        label = label.strip()
        if not label:
            raise ValueError("Ereignis-Text fehlt")
        with self.lock:
            self.logger.event(f"USER: {label}")
            return self.record_event("user", label=label)

    # ---------- app views ----------
    def status(self) -> dict:
        now = time.monotonic()
        with self.lock:
            self.assistant.tick(now)
            age_ms = None if self.last_frame_monotonic is None else round((now - self.last_frame_monotonic) * 1000, 1)
            if self.source == "demo":
                hint = ""
            elif not self.connected:
                detail = f" Letzter Fehler: {self.last_error}." if self.last_error else ""
                hint = ("USB nicht verbunden. Kabel/COM-Port pruefen; bei mehreren Ports "
                        "start_diagnose.bat --serial-port COMx verwenden." + detail +
                        " Kein automatischer Firmwarefehler.")
            elif age_ms is None or age_ms > 3000:
                hint = ("Keine CAN-Frames. Moegliche Ursachen: Gateway/Anschlussstelle, Bitrate, "
                        "CAN H/L, Terminierung. Kein automatischer Firmwarefehler.")
            else:
                hint = ""
            return {
                "source": self.source,
                "profile": self.profile,
                "demo_mode": self.demo_mode,
                "demo_flag": self.demo_flag,
                "connected": self.connected,
                "serial_port": self.serial_port,
                "last_error": self.last_error,
                "session": {
                    "stem": self.session_stem,
                    "csv": str(self.logger.session_path),
                    "events_log": str(self.logger.events_path),
                    "raw_jsonl": str(self.raw_path),
                    "events_jsonl": str(self.events_path),
                    "meta": str(self.meta_path),
                },
                "measurement": {"active": self.measurement_active, "name": self.measurement},
                "counters": self._counters(),
                "monitor_seq": self.monitor_seq,
                "firmware_stats": self.firmware_stats,
                "last_frame": {"age_ms": age_ms, "received_iso": self.last_frame_iso},
                "no_frames_hint": hint,
                "assistant": {
                    "phase": self.assistant.phase,
                    "run_id": self.assistant.run_id,
                    "remaining_seconds": self.assistant.status(now)["remaining_seconds"],
                    "action_label": self.assistant.action_label,
                },
                "signal_count": len(self.store.signals),
                "generated_config": str(self.store.generated_path),
            }

    def signals(self) -> list:
        with self.lock:
            self.assistant.tick()
            return self.runtime.snapshot(time.monotonic())

    def recent_frames(self, limit: int = 100) -> list:
        with self.lock:
            return list(self.frames)[-max(1, min(limit, 300)):]

    def monitor(self, since: int = 0, limit: int = 300, id_filter: str = "",
                frame_type: str = "all") -> dict:
        limit = max(1, min(int(limit), 1000))
        now = time.monotonic()
        with self.lock:
            while self.rate_samples and now - self.rate_samples[0][0] > 2.0:
                self.rate_samples.popleft()
            total_rate = len(self.rate_samples) / 2.0
            per_id = Counter(can_id for _, can_id in self.rate_samples)
            needle = id_filter.strip().lower().replace("0x", "")
            frames = [frame for frame in self.frames if int(frame.get("monitor_seq", 0)) > since]
            if needle:
                frames = [frame for frame in frames if needle in f"{int(frame.get('id', 0)):X}".lower()]
            if frame_type == "std":
                frames = [frame for frame in frames if not frame.get("extended")]
            elif frame_type == "ext":
                frames = [frame for frame in frames if frame.get("extended")]
            frames = frames[-limit:]
            oldest = int(self.frames[0].get("monitor_seq", 0)) if self.frames else 0
            missed = max(0, oldest - int(since) - 1) if since and oldest else 0
            return {
                "frames": frames,
                "latest_seq": self.monitor_seq,
                "oldest_seq": oldest,
                "missed_frames": missed,
                "total_rate": round(total_rate, 1),
                "rates": [
                    {"id": can_id, "id_hex": f"0x{can_id:03X}", "rate": round(count / 2.0, 1)}
                    for can_id, count in sorted(per_id.items())
                ],
                "unique_ids": len(per_id),
                "demo_mode": self.demo_mode,
                "connected": self.connected,
                "measurement": {"active": self.measurement_active, "name": self.measurement},
                "counters": self._counters(),
                "firmware_stats": self.firmware_stats,
            }

    def events_since(self, since: int = 0) -> list:
        with self.lock:
            return [event for event in self.events if int(event.get("id", 0)) > since]

    def references(self) -> dict:
        return self.store.references()

    def assistant_data(self) -> dict:
        with self.lock:
            return self.assistant.status()

    # ---------- assistant ----------
    def assistant_start(self, action_label: str = "") -> dict:
        with self.lock:
            if self.assistant.phase not in {"idle", "evaluated"}:
                raise ValueError("Pruefablauf laeuft bereits; bitte zuerst zuruecksetzen")
            self.assistant.start(action_label)
            self.record_event("assistant_start", action_label=action_label, run_id=self.assistant.run_id)
            return self.assistant.status()

    def assistant_mark(self, label: str = "") -> dict:
        with self.lock:
            status = self.assistant.mark_action(label)
            self.record_event("assistant_action", action_label=self.assistant.action_label,
                              run_id=self.assistant.run_id)
            return status

    def assistant_evaluate(self) -> dict:
        with self.lock:
            status = self.assistant.evaluate()
            self.record_event("assistant_evaluate", run_id=self.assistant.run_id,
                              candidates=len(status["candidates"]))
            return status

    def assistant_reset(self) -> dict:
        with self.lock:
            self.assistant.reset()
            self.record_event("assistant_reset")
            return self.assistant.status()

    def assistant_bind(self, signal_id: str, candidate_index: int) -> dict:
        with self.lock:
            if self.assistant.phase != "evaluated":
                raise ValueError("Zuerst den Pruefablauf auswerten")
            if not 0 <= candidate_index < len(self.assistant.candidates):
                raise ValueError("Kandidat ungueltig")
            if not self.assistant.action_label:
                raise ValueError("Aktionsbezeichnung fehlt")
            candidate = self.assistant.candidates[candidate_index]
            signal = self.store.apply_candidate(
                signal_id,
                candidate,
                self.assistant.run_id or "",
                self.assistant.action_label,
                self.measurement,
                self.demo_mode,
            )
            self.record_event("assistant_bind", signal_id=signal_id, candidate=candidate,
                              run_id=self.assistant.run_id)
            return signal

    # ---------- editor / confirmation ----------
    def save_signal(self, payload: dict) -> dict:
        with self.lock:
            signal = self.store.upsert(payload)
            self.record_event("signal_saved", signal_id=signal["id"], status=signal["status"])
            return signal

    def set_signal_status(self, signal_id: str, status: str) -> dict:
        with self.lock:
            signal = self.store.set_status(signal_id, status)
            self.record_event("signal_status", signal_id=signal_id, status=status)
            return signal

    def confirm_signal(self, signal_id: str, note: str, checklist: bool) -> dict:
        with self.lock:
            signal = self.store.confirm(signal_id, note, checklist)
            self.record_event("signal_confirmed", signal_id=signal_id,
                              confirmed_note=signal.get("confirmed_note", ""))
            return signal

    def toggle_demo(self) -> dict:
        if not self.demo_mode:
            raise ValueError("Demo-Umschaltung nur im Demo-Modus")
        with self.lock:
            self.demo_flag = not self.demo_flag
            self.record_event("demo_action", value="EIN" if self.demo_flag else "AUS")
            return {"demo_flag": self.demo_flag}

    # ---------- exports ----------
    def flush_files(self) -> None:
        with self.lock:
            self.raw_file.flush()
            self.events_file.flush()

    def export_files(self) -> dict:
        self.flush_files()
        files = []
        for path in sorted(self.output_dir.glob("*")):
            if path.is_file():
                files.append({"name": path.name, "size": path.stat().st_size})
        return {
            "session": str(self.logger.session_path),
            "raw_jsonl": str(self.raw_path),
            "events_jsonl": str(self.events_path),
            "meta": str(self.meta_path),
            "files": files,
            "generated": str(self.store.generated_path),
            "confirmed": str(self.store.confirmed_path),
        }

    def resolve_export(self, name: str) -> Path:
        candidate = (self.output_dir / Path(name).name).resolve()
        if self.output_dir.resolve() not in candidate.parents:
            raise ValueError("Ungueltiger Dateiname")
        if not candidate.is_file():
            raise ValueError("Datei nicht gefunden")
        return candidate

    def measurement_files(self) -> list:
        return sorted([path.name for path in self.output_dir.glob("*.csv") if not path.name.startswith("session_")])

    # ---------- source threads ----------
    def start(self) -> None:
        if self.demo_mode:
            self.thread = threading.Thread(target=self._demo_loop, name="demo", daemon=True)
            self.thread.start()
        else:
            self.line_queue = queue.Queue(maxsize=200000)
            self.reader_thread = threading.Thread(target=self._serial_reader_loop, name="serial-reader", daemon=True)
            self.processor_thread = threading.Thread(target=self._processor_loop, name="serial-processor", daemon=True)
            self.thread = self.reader_thread
            self.reader_thread.start()
            self.processor_thread.start()

    def _serial_reader_loop(self) -> None:
        """Liest den COM-Port zuegig und legt Rohzeilen in die Queue.

        Die eigentliche Verarbeitung (CSV, Signal-Engine, HTTP-Daten) laeuft
        im Processor-Thread. So wird der USB-Puffer auch bei kurzen
        Schreib-/Analyse-Pausen schnell geleert.
        """
        port = self.serial_port
        connection = None
        while not self.stop_event.is_set():
            if not port:
                port = find_esp_port()
                if not port:
                    self.on_connection(False, None, "Kein ESP-Port gefunden")
                    self.stop_event.wait(2.0)
                    continue
            try:
                connection = open_serial(port, self.baud)
                self.on_connection(True, port)
                buffer = b""
                while not self.stop_event.is_set():
                    chunk = connection.read(4096)
                    if not chunk or self.line_queue is None:
                        continue
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if not line:
                            continue
                        try:
                            self.line_queue.put_nowait(line + b"\n")
                        except queue.Full:
                            self.line_queue_dropped += 1
            except (serial.SerialException, OSError) as error:
                self.on_connection(False, port, str(error))
                if not self.serial_port_locked:
                    port = find_esp_port()
                self.stop_event.wait(2.0)
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        pass
                    connection = None

    def _processor_loop(self) -> None:
        while not self.stop_event.is_set() or (self.line_queue is not None and not self.line_queue.empty()):
            if self.line_queue is None:
                break
            try:
                raw = self.line_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            text = raw.decode("utf-8", errors="replace")
            kind, payload = parse_line(text)
            if kind == "can" and payload is not None:
                self.ingest(payload)
            elif kind == "diag" and payload is not None:
                self.on_diag(str(payload.get("message", "")))
            else:
                self.on_raw_line(text)

    def _demo_loop(self) -> None:
        start = time.monotonic()
        next_times = {"speed": start, "status": start, "battery": start, "temp": start}
        sequence = 0
        while not self.stop_event.is_set():
            now = time.monotonic()
            elapsed = now - start
            timestamp_us = int(elapsed * 1_000_000)
            ambient = int((elapsed // 8.0) % 2) == 1
            frames = []
            if now >= next_times["speed"]:
                value = int(50 + (elapsed * 20) % 60)
                frames.append((0x100, bytes([value & 0xFF, (value >> 8) & 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])))
                next_times["speed"] += 0.10
            if now >= next_times["status"]:
                flags = (0x01 if self.demo_flag else 0x00) | (0x02 if ambient else 0x00)
                frames.append((0x1A0, bytes([flags, sequence & 0xFF, (sequence >> 8) & 0xFF, 0x5A, 0x00, 0x00, 0x00, 0x00])))
                next_times["status"] += 0.20
                sequence += 1
            if now >= next_times["battery"]:
                frames.append((0x3E0, bytes([0x10 + (sequence % 80), 0x33, 0x50, 0x20, 0x00, 0x00, 0x00, 0x00])))
                next_times["battery"] += 0.50
            if now >= next_times["temp"]:
                frames.append((0x2C0, bytes([0x14 + (sequence % 10), 0x1E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])))
                next_times["temp"] += 1.0
            for can_id, data in frames:
                self.ingest(
                    {
                        "seq": sequence,
                        "timestamp_us": timestamp_us,
                        "id": can_id,
                        "extended": False,
                        "dlc": 8,
                        "data": data.hex().upper(),
                        "demo": True,
                        "received_iso": utc_now_iso(),
                    }
                )
            self.stop_event.wait(0.02)

    def shutdown(self) -> None:
        self.stop_event.set()
        for thread in (self.thread, self.reader_thread, self.processor_thread):
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout=3.0)
        with self.lock:
            if self.measurement_active and self.measurement:
                self.runtime.finalize_measurement(self.measurement)
                self.measurement_active = False
            self._write_meta()
            try:
                self.logger.close()
            finally:
                self.raw_file.close()
                self.events_file.close()


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, app: DiagnosticsApp) -> None:
        super().__init__(address, handler)
        self.app = app


class Handler(BaseHTTPRequestHandler):
    server_version = "VolvoCANLocal/1.0"

    @property
    def app(self) -> DiagnosticsApp:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keine Frame-/Request-Flut in der Konsole.
        return

    def _send_json(self, payload: Any, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code: int, message: str) -> None:
        self._send_json({"ok": False, "error": message}, code)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Ungueltiges JSON: {exc}") from exc

    def _send_file(self, path: Path, download: bool = True) -> None:
        if not path.is_file():
            self._error(404, "Datei nicht gefunden")
            return
        content_type = CONTENT_TYPES.get(path.suffix.lower(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        with path.open("rb") as handle:
            shutil.copyfileobj(handle, self.wfile)

    def _csv_to_json(self, path: Path) -> None:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self._send_json({"file": path.name, "rows": rows})

    def _jsonl_to_json(self, path: Path) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Disposition", f'attachment; filename="{path.stem}.json"')
        self.end_headers()
        self.wfile.write(b"[")
        first = True
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                if not first:
                    self.wfile.write(b",")
                self.wfile.write(line.encode("utf-8"))
                first = False
        self.wfile.write(b"]")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path in {"/", "/index.html"}:
                self._send_file(WEB_ROOT / "index.html", download=False)
            elif path in {"/style.css", "/app.js"}:
                self._send_file(WEB_ROOT / path.lstrip("/"), download=False)
            elif path == "/api/status":
                self._send_json(self.app.status())
            elif path == "/api/signals":
                self._send_json({"signals": self.app.signals()})
            elif path == "/api/references":
                self._send_json(self.app.references())
            elif path == "/api/events":
                since = int(query.get("since", ["0"])[0])
                self._send_json({"events": self.app.events_since(since)})
            elif path == "/api/frames":
                limit = int(query.get("limit", ["100"])[0])
                self._send_json({"frames": self.app.recent_frames(limit)})
            elif path == "/api/monitor":
                since = int(query.get("since", ["0"])[0])
                limit = int(query.get("limit", ["300"])[0])
                id_filter = query.get("id", [""])[0]
                frame_type = query.get("type", ["all"])[0]
                self._send_json(self.app.monitor(since, limit, id_filter, frame_type))
            elif path == "/api/assistant":
                self._send_json({"assistant": self.app.assistant_data(), "scenarios": SCENARIOS})
            elif path == "/api/export/list":
                self._send_json(self.app.export_files())
            elif path == "/api/export/session":
                fmt = query.get("format", ["csv"])[0].lower()
                if fmt == "jsonl":
                    self.app.flush_files()
                    self._send_file(self.app.raw_path)
                elif fmt == "json":
                    self.app.flush_files()
                    self._jsonl_to_json(self.app.raw_path)
                else:
                    self._send_file(self.app.logger.session_path)
            elif path == "/api/export/measurement":
                name = query.get("name", [""])[0]
                fmt = query.get("format", ["csv"])[0].lower()
                target = self.app.resolve_export(name)
                if fmt == "json":
                    self._csv_to_json(target)
                else:
                    self._send_file(target)
            elif path == "/api/export/events":
                self.app.flush_files()
                if query.get("format", ["jsonl"])[0].lower() == "json":
                    self._jsonl_to_json(self.app.events_path)
                else:
                    self._send_file(self.app.events_path)
            elif path == "/api/export/generated":
                self._send_file(Path(self.app.store.generated_path))
            elif path == "/api/export/confirmed":
                self._send_file(Path(self.app.store.confirmed_path))
            elif path == "/api/health":
                self._send_json({"ok": True, "service": "volvo-can-diagnostics",
                                 "profile": self.app.profile})
            elif path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            else:
                self._error(404, "Nicht gefunden")
        except Exception as exc:
            self._error(500, str(exc))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/event/mark":
                self._send_json(self.app.mark_event(str(body.get("label", ""))))
            elif path == "/api/measurement/start":
                self._send_json(self.app.start_measurement(str(body.get("name", ""))))
            elif path == "/api/measurement/stop":
                self._send_json(self.app.stop_measurement())
            elif path == "/api/signals":
                self._send_json(self.app.save_signal(body))
            elif path == "/api/signals/status":
                self._send_json(self.app.set_signal_status(str(body.get("id", "")), str(body.get("status", ""))))
            elif path == "/api/signals/confirm":
                self._send_json(self.app.confirm_signal(str(body.get("id", "")), str(body.get("note", "")),
                                                         bool(body.get("checklist"))))
            elif path == "/api/assistant/start":
                self._send_json(self.app.assistant_start(str(body.get("action_label", ""))))
            elif path == "/api/assistant/mark_action":
                self._send_json(self.app.assistant_mark(str(body.get("action_label", ""))))
            elif path == "/api/assistant/evaluate":
                self._send_json(self.app.assistant_evaluate())
            elif path == "/api/assistant/bind":
                self._send_json(self.app.assistant_bind(str(body.get("signal_id", "")), int(body.get("candidate_index", -1))))
            elif path == "/api/assistant/reset":
                self._send_json(self.app.assistant_reset())
            elif path == "/api/demo/toggle":
                self._send_json(self.app.toggle_demo())
            else:
                self._error(404, "Nicht gefunden")
        except (ValueError, KeyError, TypeError) as exc:
            self._error(400, str(exc))
        except Exception as exc:
            self._error(500, str(exc))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Volvo CAN Control - lokale Diagnoseoberflaeche")
    parser.add_argument("--host", default="127.0.0.1", help="Bind-Adresse (nur lokal empfohlen)")
    parser.add_argument("--port", type=int, default=8765, help="HTTP-Port (Standard 8765)")
    parser.add_argument("--serial-port", default=None, help="COM-Port, z. B. COM5 (sonst automatische Erkennung)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--config-dir", default=str(ROOT / "config"))
    parser.add_argument("--output-dir", default=str(ROOT / "messungen"))
    parser.add_argument("--demo", action="store_true", help="Synthetische DEMO-Frames, kein USB")
    parser.add_argument("--profile", default="OBD-Low-Bus", help="Projektprofil, z. B. OBD-Low-Bus oder OBD-CEM-Bus")
    parser.add_argument("--list-ports", action="store_true", help="Serielle Ports anzeigen und beenden")
    args = parser.parse_args(argv)

    if args.list_ports:
        for entry in list_ports.comports():
            print(f"{entry.device} - {entry.description}")
        return 0

    app = DiagnosticsApp(Path(args.config_dir), Path(args.output_dir), demo=args.demo,
                         serial_port=args.serial_port, baud=args.baud, profile=args.profile)
    try:
        server = LocalServer((args.host, args.port), Handler, app)
    except OSError as exc:
        print(f"Port {args.port} kann nicht geoeffnet werden: {exc}")
        app.shutdown()
        return 1
    app.start()
    print(f"Volvo CAN Diagnose: http://{args.host}:{args.port}")
    print(f"Quelle: {'DEMO' if args.demo else 'USB-CDC'} | Session: {app.logger.session_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        app.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
