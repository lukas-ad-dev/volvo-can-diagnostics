#!/usr/bin/env python3
"""Erzeugt src/web_ui.cpp aus den Dateien unter web/.

Nach Aenderungen an der Weboberflaeche ausfuehren:
    python tools/build_web.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUT_CPP = ROOT / "firmware" / "src" / "web_ui.cpp"
OUT_H = ROOT / "firmware" / "src" / "web_ui.h"
DELIM = "VCCUI"


def raw(name: str, path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    marker = f"){DELIM}\""
    if marker in text:
        raise SystemExit(f"Raw-String-Marker {marker!r} kommt in {path} vor")
    return f'const char {name}[] PROGMEM = R"{DELIM}({text}){DELIM}";\n'


def main() -> None:
    parts = [
        '#include "web_ui.h"\n',
        "#include <Arduino.h>\n\n",
        raw("VOLVO_INDEX_HTML", WEB / "index.html"),
        raw("VOLVO_STYLE_CSS", WEB / "style.css"),
        raw("VOLVO_APP_JS", WEB / "app.js"),
    ]
    OUT_CPP.write_text("\n".join(parts), encoding="utf-8")
    OUT_H.write_text(
        "#pragma once\n\n"
        "#include <Arduino.h>\n\n"
        "extern const char VOLVO_INDEX_HTML[];\n"
        "extern const char VOLVO_STYLE_CSS[];\n"
        "extern const char VOLVO_APP_JS[];\n",
        encoding="utf-8",
    )
    print(f"geschrieben: {OUT_CPP}")
    print(f"geschrieben: {OUT_H}")


if __name__ == "__main__":
    main()
