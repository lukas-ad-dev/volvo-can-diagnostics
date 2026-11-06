#!/usr/bin/env python3
"""Volvo CAN Control - Windows-USB-Logger fuer USB-CDC.

Liest das NDJSON-Format des ESP32 (eine JSON-Zeile pro CAN-Frame),
zeigt Frames live an und schreibt sie fortlaufend in:
  - eine Session-CSV (alles ab Programmstart)
  - optional benannte Messdateien (Szenarien 1-10 oder freier Name)

Diagnosemeldungen des ESP beginnen mit "# " und werden in eine separate
Event-Logdatei geschrieben. Das Programm benoetigt nur pyserial.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import queue
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("Fehler: pyserial ist nicht installiert.")
    print("Installation:  python -m pip install pyserial")
    raise SystemExit(2)

CSV_FIELDS = [
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

SCENARIOS: Dict[str, Tuple[str, str]] = {
    "1": ("01_fahrzeug_verriegelt", "Fahrzeug verriegelt"),
    "2": ("02_fahrzeug_entriegeln", "Fahrzeug entriegeln"),
    "3": ("03_fahrertuer_oeffnen", "Fahrertuer oeffnen"),
    "4": ("04_zuendung_aktivieren", "Zuendung aktivieren"),
    "5": ("05_rueckwaertsgang", "Rueckwaertsgang einlegen"),
    "6": ("06_abblendlicht", "Abblendlicht einschalten"),
    "7": ("07_fernlicht", "Fernlicht einschalten"),
    "8": ("08_parkkamera_manuell", "Parkkamera manuell aktivieren"),
    "9": ("09_radio_aus_auto", "Radio bei ausgeschaltetem Fahrzeug"),
    "10": ("10_verriegeln_can_aktivitaet", "Verriegeln und CAN-Aktivitaet beobachten"),
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    slug = slug.strip("_")
    return slug[:60] or "messung"


def scenario_name(value: str) -> str:
    if value in SCENARIOS:
        return SCENARIOS[value][0]
    return slugify(value)


def parse_line(line: str) -> Tuple[str, Optional[dict]]:
    """Erkennt CAN-Zeilen, Diagnosezeilen und sonstige Bootmeldungen."""
    text = line.strip()
    if not text:
        return "empty", None
    if text.startswith("#"):
        return "diag", {"message": text}
    if not text.startswith("{"):
        return "raw", {"message": text}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return "raw", {"message": text}
    if not isinstance(payload, dict):
        return "raw", {"message": text}
    if payload.get("type") == "can":
        required = {"seq", "timestamp_us", "id", "extended", "dlc", "data", "demo"}
        if required.issubset(payload):
            return "can", payload
    if payload.get("type") == "diag":
        return "diag", {"message": str(payload.get("message", text))}
    return "raw", {"message": text}


def frame_row(frame: dict, measurement: str) -> List[object]:
    can_id = int(frame["id"])
    extended = bool(frame["extended"])
    width = 8 if extended else 3
    can_id_hex = str(frame.get("id_hex") or f"0x{can_id:0{width}X}")
    data_hex = re.sub(r"[^0-9A-Fa-f]", "", str(frame.get("data", ""))).upper()
    data_hex = data_hex.ljust(16, "0")[:16]
    return [
        measurement,
        int(frame.get("seq", 0)),
        int(frame.get("timestamp_us", 0)),
        can_id_hex,
        can_id,
        1 if extended else 0,
        int(frame.get("dlc", 0)),
        data_hex,
        1 if frame.get("demo") else 0,
        iso_now(),
    ]


def find_esp_port() -> Optional[str]:
    candidates = []
    for port in list_ports.comports():
        text = f"{port.device} {port.description} {port.manufacturer or ''}".lower()
        if port.vid == 0x303A or any(
            needle in text for needle in ("espressif", "usb jtag", "usb serial", "usb cdc", "waveshare")
        ):
            candidates.append(port.device)
    if len(candidates) == 1:
        return candidates[0]
    return None


def choose_port(requested: Optional[str], interactive: bool = True) -> Optional[str]:
    if requested:
        return requested
    port = find_esp_port()
    if port:
        return port
    ports = list(list_ports.comports())
    if not ports:
        print("Kein COM-Port gefunden. USB-Kabel pruefen, Board neu verbinden.")
        return None
    print("Verfuegbare serielle Ports:")
    for index, entry in enumerate(ports, start=1):
        print(f"  [{index}] {entry.device} - {entry.description}")
    if not interactive:
        return ports[0].device
    try:
        choice = input("Port-Nummer waehlen (Enter = 1): ").strip()
    except EOFError:
        return ports[0].device
    if not choice:
        return ports[0].device
    try:
        return ports[int(choice) - 1].device
    except (ValueError, IndexError):
        print("Ungueltige Auswahl; verwende ersten Port.")
        return ports[0].device


class Logger:
    def __init__(self, output_dir: Path, quiet: bool = False) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quiet = quiet
        self.lock = threading.Lock()
        self.print_lock = threading.Lock()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.session_path = self.output_dir / f"session_{stamp}.csv"
        self.events_path = self.output_dir / f"session_{stamp}_events.log"
        self.session_file = self.session_path.open("w", newline="", encoding="utf-8")
        self.session_writer = csv.writer(self.session_file, lineterminator="\n")
        self.session_writer.writerow(CSV_FIELDS)
        self.session_file.flush()
        self.events_file = self.events_path.open("a", encoding="utf-8")
        self.measurement_name = ""
        self.measurement_path: Optional[Path] = None
        self.measurement_file = None
        self.measurement_writer = None
        self.measurement_frames = 0
        self.session_frames = 0
        self.last_flush = time.monotonic()
        self.display_queue: "queue.Queue[str]" = queue.Queue(maxsize=600)
        self.display_dropped = 0
        self.stop_display = False
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        self.event(f"Session gestartet: {self.session_path.name}")

    def _display_loop(self) -> None:
        while not self.stop_display:
            try:
                line = self.display_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            with self.print_lock:
                print(line, flush=True)

    def _write_event_line(self, text: str) -> None:
        self.events_file.write(text + "\n")
        self.events_file.flush()

    def event(self, message: str) -> None:
        line = f"{iso_now()} [EVENT] {message}"
        with self.lock:
            self._write_event_line(line)
        with self.print_lock:
            print(f"[EVENT] {message}", flush=True)

    def diagnostic(self, message: str) -> None:
        line = f"{iso_now()} [DIAG] {message}"
        with self.lock:
            self._write_event_line(line)
        with self.print_lock:
            print(f"[DIAG] {message}", flush=True)

    def start_measurement(self, name: str) -> bool:
        with self.lock:
            if self.measurement_file is not None:
                return False
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = self.output_dir / f"{stamp}_{slugify(name)}.csv"
            handle = path.open("w", newline="", encoding="utf-8")
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(CSV_FIELDS)
            handle.flush()
            self.measurement_name = slugify(name)
            self.measurement_path = path
            self.measurement_file = handle
            self.measurement_writer = writer
            self.measurement_frames = 0
            self._write_event_line(f"{iso_now()} [EVENT] Messung gestartet: {path.name}")
        with self.print_lock:
            print(f"[MESSUNG] gestartet: {path.name}", flush=True)
        return True

    def stop_measurement(self) -> Optional[Path]:
        with self.lock:
            if self.measurement_file is None:
                return None
            path = self.measurement_path
            frames = self.measurement_frames
            self.measurement_file.flush()
            self.measurement_file.close()
            self.measurement_file = None
            self.measurement_writer = None
            self.measurement_name = ""
            self.measurement_path = None
            self._write_event_line(f"{iso_now()} [EVENT] Messung gestoppt: {path.name} ({frames} Frames)")
        with self.print_lock:
            print(f"[MESSUNG] gestoppt: {path.name} ({frames} Frames)", flush=True)
        return path

    def record(self, frame: dict) -> None:
        with self.lock:
            measurement = self.measurement_name
            row = frame_row(frame, measurement)
            self.session_writer.writerow(row)
            self.session_frames += 1
            if self.measurement_writer is not None:
                self.measurement_writer.writerow(row)
                self.measurement_frames += 1
            now = time.monotonic()
            if self.session_frames % 200 == 0 or (now - self.last_flush) >= 2.0:
                self.session_file.flush()
                if self.measurement_file is not None:
                    self.measurement_file.flush()
                self.last_flush = now
        if not self.quiet:
            text = (
                f"{int(frame['timestamp_us']) / 1e6:10.6f}  "
                f"{str(frame.get('id_hex', '')):>10}  "
                f"{'EXT' if frame['extended'] else 'STD':3}  "
                f"DLC {int(frame['dlc'])}  "
                f"{str(frame['data'])}"
                f"{'  DEMO' if frame.get('demo') else ''}"
                f"{'  [' + measurement + ']' if measurement else ''}"
            )
            try:
                self.display_queue.put_nowait(text)
            except queue.Full:
                self.display_dropped += 1

    def status_text(self) -> str:
        with self.lock:
            active = self.measurement_name or "-"
            return (
                f"Session-Frames: {self.session_frames} | "
                f"Messung: {active} ({self.measurement_frames}) | "
                f"Anzeige verworfen: {self.display_dropped}"
            )

    def close(self) -> None:
        self.stop_measurement()
        self.stop_display = True
        self.display_thread.join(timeout=1.0)
        with self.lock:
            self.session_file.flush()
            self.session_file.close()
            self._write_event_line(f"{iso_now()} [EVENT] Session beendet: {self.session_frames} Frames")
            self.events_file.close()


def open_serial(port: str, baud: int) -> "serial.Serial":
    connection = serial.Serial(
        port=port,
        baudrate=baud,
        timeout=0.2,
        write_timeout=0,
        rtscts=False,
        dsrdtr=False,
    )
    try:
        # ESP32-S3 Auto-Reset: DTR/RTS nicht halten, sonst bleibt das Board
        # im Reset/Bootloader und sendet keine Zeilen.
        connection.dtr = False
        connection.rts = False
    except Exception:
        pass
    try:
        connection.reset_input_buffer()
    except Exception:
        pass
    return connection


def reader_loop(logger: Logger, port: str, baud: int, stop_event: threading.Event,
                max_frames: int) -> None:
    frames = 0
    current_port = port
    while not stop_event.is_set():
        try:
            logger.event(f"Verbinde mit {current_port} ...")
            connection = open_serial(current_port, baud)
            logger.event(f"Verbunden mit {current_port}")
            while not stop_event.is_set():
                raw = connection.readline()
                if not raw:
                    continue
                kind, payload = parse_line(raw.decode("utf-8", errors="replace"))
                if kind == "can" and payload is not None:
                    logger.record(payload)
                    frames += 1
                    if max_frames and frames >= max_frames:
                        logger.event(f"Maximalzahl {max_frames} Frames erreicht; beende.")
                        stop_event.set()
                        break
                elif kind in ("diag", "raw") and payload is not None:
                    logger.diagnostic(str(payload.get("message", "")))
            connection.close()
        except (serial.SerialException, OSError) as error:
            logger.event(f"Verbindung unterbrochen: {error}")
            time.sleep(2.0)
            replacement = find_esp_port()
            if replacement:
                current_port = replacement
    logger.event("Reader beendet.")


def print_help() -> None:
    print("""
Befehle:
  1 .. 10        Messung mit vordefiniertem Szenario starten
  r <Name>       freie Messung starten (z. B. r kamera_an)
  s              laufende Messung stoppen
  l              Messdateien im Ausgabeordner anzeigen
  i              Status anzeigen
  h              Hilfe anzeigen
  q              Programm beenden

Szenarien:
  1  Fahrzeug verriegelt
  2  Fahrzeug entriegeln
  3  Fahrertuer oeffnen
  4  Zuendung aktivieren
  5  Rueckwaertsgang einlegen
  6  Abblendlicht einschalten
  7  Fernlicht einschalten
  8  Parkkamera manuell aktivieren
  9  Radio bei ausgeschaltetem Fahrzeug weiterlaufen lassen
 10  Fahrzeug verriegeln und CAN-Aktivitaet beobachten
""")


def interactive_loop(logger: Logger, scenario_arg: Optional[str], headless: bool,
                     max_frames: int, stop_event: threading.Event) -> None:
    if scenario_arg:
        logger.start_measurement(scenario_name(scenario_arg))
    if headless:
        while not stop_event.is_set():
            time.sleep(0.2)
        return
    print_help()
    while not stop_event.is_set():
        try:
            command = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            stop_event.set()
            break
        if not command:
            continue
        lower = command.lower()
        if lower in ("q", "quit", "exit"):
            stop_event.set()
            break
        if lower in ("h", "help", "?"):
            print_help()
        elif lower in ("s", "stop", "x"):
            if logger.stop_measurement() is None:
                print("Keine Messung aktiv.")
        elif lower in ("i", "status"):
            print(logger.status_text())
        elif lower in ("l", "list"):
            files = sorted(logger.output_dir.glob("*_*.csv"))
            for path in files:
                print(" ", path.name)
            if not files:
                print("  (keine Messdateien)")
        elif command in SCENARIOS:
            print(f"[SZENARIO] {SCENARIOS[command][1]}")
            if not logger.start_measurement(SCENARIOS[command][0]):
                print("Es laeuft bereits eine Messung; bitte zuerst mit 's' stoppen.")
        elif lower.startswith("r "):
            name = command[2:].strip()
            if not name:
                print("Name fehlt, z. B. 'r kamera_an'.")
            elif not logger.start_measurement(name):
                print("Es laeuft bereits eine Messung; bitte zuerst mit 's' stoppen.")
        else:
            print("Unbekannter Befehl. 'h' zeigt die Hilfe.")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Volvo CAN Control USB-CDC-Logger")
    parser.add_argument("--port", help="COM-Port, z. B. COM5 (sonst automatische Erkennung)")
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate (USB-CDC, Standard 115200)")
    parser.add_argument("--output-dir", default="messungen", help="Zielordner (Standard: messungen)")
    parser.add_argument("--auto-measurement", help="Messung sofort starten (Name oder Szenario 1-10)")
    parser.add_argument("--max-frames", type=int, default=0, help="Nach N CAN-Frames beenden (Tests)")
    parser.add_argument("--quiet", action="store_true", help="Keine Live-Frame-Ausgabe")
    parser.add_argument("--headless", action="store_true", help="Keine interaktiven Befehle (Tests)")
    parser.add_argument("--list-ports", action="store_true", help="Nur COM-Ports anzeigen")
    args = parser.parse_args(argv)

    if args.list_ports:
        for entry in list_ports.comports():
            print(f"{entry.device} - {entry.description}")
        return 0

    port = choose_port(args.port, interactive=not args.headless)
    if port is None:
        return 1

    logger = Logger(Path(args.output_dir), quiet=args.quiet)
    stop_event = threading.Event()
    reader = threading.Thread(
        target=reader_loop,
        args=(logger, port, args.baud, stop_event, args.max_frames),
        daemon=True,
    )
    reader.start()
    try:
        interactive_loop(logger, args.auto_measurement, args.headless, args.max_frames, stop_event)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        stop_event.set()
        reader.join(timeout=2.0)
        logger.close()
        print(f"\nSession: {logger.session_path}")
        print(f"Events:  {logger.events_path}")
        print(logger.status_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
