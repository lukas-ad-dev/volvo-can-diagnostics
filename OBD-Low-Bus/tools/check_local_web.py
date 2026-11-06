#!/usr/bin/env python3
"""Statischer Check fuer die lokale Diagnose-Weboberflaeche."""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "local_web" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "local_web" / "app.js").read_text(encoding="utf-8")
SERVER = (ROOT / "tools" / "local_can_diagnostics.py").read_text(encoding="utf-8")


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])


def main() -> int:
    parser = IdParser()
    parser.feed(HTML)
    ids = set(parser.ids)
    used = set(re.findall(r'\$\("([^"]+)"\)', JS))
    missing = sorted(used - ids)
    if missing:
        print("Fehlende HTML-IDs:", missing)
        return 1
    endpoints = set(re.findall(r'api\(["`](/api/[^"?`]+)', JS))
    missing_endpoints = [endpoint for endpoint in endpoints if f'"{endpoint}"' not in SERVER]
    if missing_endpoints:
        print("Unbekannte API-Pfade:", missing_endpoints)
        return 1
    external = re.findall(r'https?://[^\s"\'<>]+', HTML + JS)
    if external:
        print("Unerwartete externe URLs:", external)
        return 1
    print(f"OK: {len(ids)} HTML-IDs, {len(used)} JS-IDs, {len(endpoints)} API-Pfade, keine externen Ressourcen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
