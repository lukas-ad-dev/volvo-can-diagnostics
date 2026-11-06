#!/usr/bin/env python3
"""Statischer Check fuer die Weboberflaeche."""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
SERVER = (ROOT / "firmware" / "src" / "web_server.cpp").read_text(encoding="utf-8")


class IdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if "id" in values and values["id"]:
            self.ids.append(values["id"])


def main() -> int:
    parser = IdParser()
    parser.feed(HTML)
    ids = set(parser.ids)
    used = set(re.findall(r'\$\("([^"]+)"\)', JS))
    missing = sorted(used - ids)
    if missing:
        print("Fehlende HTML-IDs fuer app.js:", missing)
        return 1

    endpoints = set(re.findall(r'fetch\w*\("(/api/[^"?]+)', JS))
    missing_endpoints = [endpoint for endpoint in endpoints if f'"{endpoint}"' not in SERVER]
    if missing_endpoints:
        print("In app.js verwendet, aber im Webserver unbekannt:", missing_endpoints)
        return 1

    external = re.findall(r'https?://[^\s"\'<>]+', HTML + JS)
    unexpected = [url for url in external if not url.startswith("http://192.168.4.1")]
    if unexpected:
        print("Unerwartete externe URLs:", unexpected)
        return 1

    print(f"OK: {len(ids)} HTML-IDs, {len(used)} JS-IDs, {len(endpoints)} API-Pfade, keine CDN-Abhaengigkeit.")
    print(f"CSS-Regeln: {CSS.count('{')}, JS-Zeilen: {len(JS.splitlines())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
