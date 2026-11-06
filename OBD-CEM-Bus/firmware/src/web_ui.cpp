#include "web_ui.h"

#include <Arduino.h>


const char VOLVO_INDEX_HTML[] PROGMEM = R"VCCUI(<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>Volvo CAN Control</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <div class="brand-mark">VCC</div>
      <div>
        <h1>Volvo CAN Control</h1>
        <p>Passive CAN-Analyse &middot; V0.1</p>
      </div>
    </div>
    <div id="connection" class="pill ok">Verbunden</div>
  </header>

  <div id="demo-banner" class="demo-banner hidden">
    DEMO-MODUS: Alle angezeigten Frames sind synthetisch und keine Fahrzeugdaten.
  </div>

  <nav class="tabs" aria-label="Bereiche">
    <button class="tab active" data-tab="dashboard">Dashboard</button>
    <button class="tab" data-tab="monitor">CAN-Livemonitor</button>
    <button class="tab" data-tab="compare">Signalvergleich</button>
    <button class="tab" data-tab="record">Aufzeichnung</button>
    <button class="tab" data-tab="settings">Einstellungen</button>
  </nav>

  <main>
    <section id="tab-dashboard" class="tab-panel active">
      <div class="safety">
        <strong>Sicherheitsmodus:</strong> TWAI ausschliesslich <code>LISTEN_ONLY</code>.
        Es werden keine CAN-Frames gesendet, keine Diagnoseanfragen gestellt und keine
        Fahrzeugsteuergeraete veraendert.
      </div>

      <div class="cards">
        <article class="card"><span>Quelle</span><strong id="card-source">-</strong><small id="card-source-note">-</small></article>
        <article class="card"><span>CAN-Status</span><strong id="card-state">-</strong><small>TWAI / Demo</small></article>
        <article class="card"><span>CAN-Bitrate</span><strong id="card-bitrate">-</strong><small>Fester Testbetrieb 500 kbit/s; START gesperrt</small></article>
        <article class="card"><span>Nachrichten/s</span><strong id="card-rate">-</strong><small>gleitendes 1-Sekunden-Fenster</small></article>
        <article class="card"><span>Empfangen gesamt</span><strong id="card-total">-</strong><small>seit letztem Quellwechsel</small></article>
        <article class="card"><span>Unterschiedliche IDs</span><strong id="card-ids">-</strong><small>aktuelle Beobachtung</small></article>
        <article class="card"><span>Fehler</span><strong id="card-errors">-</strong><small id="card-errors-note">TWAI-Fehler / RX-Queue voll</small></article>
        <article class="card"><span>Verworfen</span><strong id="card-dropped">-</strong><small>Live-Ring / Aufzeichnung</small></article>
        <article class="card"><span>USB-Logger</span><strong id="card-usb">-</strong><small id="card-usb-note">TX / verworfen / Fehler</small></article>
        <article class="card"><span>Arbeitsspeicher</span><strong id="card-ram">-</strong><small>freier Heap / PSRAM</small></article>
        <article class="card"><span>Systemlaufzeit</span><strong id="card-uptime">-</strong><small>seit Boot</small></article>
      </div>

      <section class="panel">
        <h2>Hinweise</h2>
        <p>
          Diese Version ist ausschliesslich fuer die passive Beobachtung gedacht.
          Die Bedeutung einzelner CAN-IDs wird nicht automatisch behauptet. Fuer belastbare
          Zuordnungen muessen Messphasen wiederholt und experimentell verglichen werden.
        </p>
        <p class="muted">
          Alle Zeitstempel sind monotone Mikrosekunden seit dem Boot des ESP32.
          Fuer lange Messungen den Python-Collector auf dem Windows-Laptop verwenden.
        </p>
      </section>
    </section>

    <section id="tab-monitor" class="tab-panel">
      <div class="toolbar">
        <label class="field">
          <span>CAN-ID filtern</span>
          <input id="filter-id" type="search" inputmode="text" placeholder="z. B. 1A0 oder 0x1A0" autocomplete="off">
        </label>
        <button id="btn-pause" class="button secondary" type="button">Pausieren</button>
        <button id="btn-clear" class="button secondary" type="button">Liste loeschen</button>
        <label class="check"><input id="sort-freq" type="checkbox"> Nach Haeufigkeit sortieren</label>
        <span id="monitor-dropped" class="muted"></span>
      </div>
      <div id="hidden-wrap" class="hidden-wrap hidden">
        <span class="muted">Ausgeblendet:</span>
        <div id="hidden-list" class="chips"></div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Zeit (s)</th>
              <th>CAN-ID</th>
              <th>Typ</th>
              <th>DLC</th>
              <th>Daten (Hex)</th>
              <th>Haeufigkeit</th>
              <th>Quelle</th>
              <th>Aktion</th>
            </tr>
          </thead>
          <tbody id="msg-body">
            <tr><td colspan="8" class="empty">Noch keine Frames. Demo-Modus kann in den Einstellungen aktiviert werden.</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section id="tab-compare" class="tab-panel">
      <div class="grid two">
        <article class="panel phase phase-a">
          <h2>Phase A &middot; vorher</h2>
          <p id="phase-a-state" class="phase-state">leer</p>
          <p class="phase-meta"><span id="phase-a-frames">0</span> Frames &middot; <span id="phase-a-duration">0,0 s</span></p>
          <div class="button-row">
            <button id="phase-a-start" class="button" type="button">Phase A starten</button>
            <button id="phase-a-stop" class="button secondary" type="button">Phase A stoppen</button>
          </div>
        </article>
        <article class="panel phase phase-b">
          <h2>Phase B &middot; nachher</h2>
          <p id="phase-b-state" class="phase-state">leer</p>
          <p class="phase-meta"><span id="phase-b-frames">0</span> Frames &middot; <span id="phase-b-duration">0,0 s</span></p>
          <div class="button-row">
            <button id="phase-b-start" class="button" type="button">Phase B starten</button>
            <button id="phase-b-stop" class="button secondary" type="button">Phase B stoppen</button>
          </div>
        </article>
      </div>

      <div class="toolbar">
        <button id="compare-refresh" class="button" type="button">Vergleich aktualisieren</button>
        <button id="compare-reset" class="button secondary" type="button">Phasen zuruecksetzen</button>
        <a id="compare-csv" class="button secondary" href="/api/compare/export?format=csv">Vergleich als CSV</a>
        <a id="compare-json" class="button secondary" href="/api/compare/export?format=json">Vergleich als JSON</a>
      </div>

      <div id="compare-result" class="compare-result">
        <p class="muted">Phase A und B starten/stoppen, dann den Vergleich aktualisieren.</p>
      </div>
    </section>

    <section id="tab-record" class="tab-panel">
      <div class="cards">
        <article class="card"><span>Status</span><strong id="record-status">bereit</strong><small>Ringpuffer im PSRAM</small></article>
        <article class="card"><span>Frames</span><strong id="record-count">0</strong><small id="record-capacity">Kapazitaet: -</small></article>
        <article class="card"><span>Verworfen</span><strong id="record-dropped">0</strong><small>Ringpuffer ueberschrieben</small></article>
      </div>
      <div class="button-row">
        <button id="record-start" class="button" type="button">Aufzeichnung starten</button>
        <button id="record-stop" class="button secondary" type="button">Aufzeichnung stoppen</button>
        <a id="download-csv" class="button secondary" href="/api/export/csv">CSV herunterladen</a>
        <a id="download-json" class="button secondary" href="/api/export/json">JSON herunterladen</a>
      </div>
      <section class="panel">
        <h2>Lange Messungen mit Windows</h2>
        <p>
          Der ESP-Ringpuffer ist begrenzt. Fuer laengere Aufzeichnungen den Python-Collector
          auf dem Laptop ausfuehren. Er verbindet sich mit dem ESP und schreibt jeden Frame
          fortlaufend in eine CSV-Datei.
        </p>
        <pre class="code">python tools\volvo_can_collector.py --host 192.168.4.1 --port 81 --output messung.csv</pre>
        <p class="muted">
          Der Download im Browser ist nur nach dem Stoppen der Aufzeichnung moeglich.
          Beim Export waehrend einer laufenden Aufzeichnung antwortet der ESP mit HTTP 409.
        </p>
      </section>
    </section>

    <section id="tab-settings" class="tab-panel">
      <section class="panel">
        <h2>CAN und Demo</h2>
        <div class="settings-grid">
          <label class="field">
            <span>CAN-Bitrate</span>
            <select id="bitrate-select">
              <option value="500" selected>500 kbit/s (fester Testbetrieb)</option>
            </select>
          </label>
          <label class="check"><input id="demo-toggle" type="checkbox"> Demo-Modus (nur synthetische DEMO-Frames, kein CAN)</label>
        </div>
        <p class="warning">
          Fester Testbetrieb mit <strong>500 kbit/s</strong> auf Basis der ausgewerteten
          Empfangsdaten. CAN bleibt beim Boot aus; der USB-Befehl <strong>START</strong> ist
          bis zur unabhaengigen Hardwarefreigabe per Compile-Flag <strong>gesperrt</strong>.
          Kein Bitratenscan, kein automatischer Start. Der Demo-Modus ist rein synthetisch
          und deaktiviert CAN.
        </p>
        <div class="button-row">
          <button id="btn-save-settings" class="button" type="button">Einstellungen speichern</button>
          <span id="settings-status" class="muted"></span>
        </div>
      </section>

      <section class="panel">
        <h2>Zugang</h2>
        <p>WLAN-AP: <strong>Volvo-CAN-Control</strong></p>
        <p>Adresse: <strong>http://192.168.4.1</strong></p>
        <p class="muted">
          Das WLAN-Passwort steht in <code>include/secrets.h</code> und in der lokalen
          Secret-Ablage des MGMT-Servers. Es wird nicht in der Weboberflaeche angezeigt.
        </p>
      </section>

      <section class="panel">
        <h2>Sicherheit</h2>
        <ul class="list">
          <li>TWAI ist ausschliesslich im Modus <code>LISTEN_ONLY</code> konfiguriert.</li>
          <li>Es gibt keinen Aufruf von <code>twai_transmit</code> und keine Diagnoseanfragen.</li>
          <li>GPIO1/GPIO2 bleiben in V0.1 hochohmig (INPUT), werden nicht angesteuert und sind nicht ueber die API schaltbar.</li>
          <li>Kein automatischer Deep Sleep; CAN-Stille wird nicht als Fahrzeug-Ruhe interpretiert.</li>
        </ul>
      </section>
    </section>
  </main>

  <footer>
    Volvo CAN Control V0.1 &middot; Nur passive, autorisierte Diagnose &middot; Keine Fahrzeugsteuerung
  </footer>

  <script src="/app.js"></script>
</body>
</html>
)VCCUI";

const char VOLVO_STYLE_CSS[] PROGMEM = R"VCCUI(:root {
  --bg: #0b1016;
  --bg-soft: #111821;
  --panel: #151d27;
  --panel-2: #1a2431;
  --line: #263344;
  --text: #e6edf5;
  --muted: #8fa1b7;
  --accent: #4cc2ff;
  --accent-2: #7ee787;
  --warn: #f0b429;
  --danger: #ff6b6b;
  --demo: #ffb86b;
  --radius: 14px;
  --shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background:
    radial-gradient(1200px 500px at 15% -10%, rgba(76, 194, 255, 0.10), transparent 60%),
    radial-gradient(900px 450px at 100% 0%, rgba(126, 231, 135, 0.06), transparent 55%),
    var(--bg);
  color: var(--text);
  font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 15px;
  line-height: 1.45;
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px clamp(16px, 3vw, 36px) 14px;
  border-bottom: 1px solid var(--line);
  background: rgba(11, 16, 22, 0.78);
  backdrop-filter: blur(8px);
  position: sticky;
  top: 0;
  z-index: 20;
}

.brand { display: flex; align-items: center; gap: 14px; }
.brand-mark {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: #061018;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  box-shadow: 0 8px 24px rgba(76, 194, 255, 0.25);
}
h1 { margin: 0; font-size: 1.15rem; letter-spacing: 0.02em; }
.topbar p { margin: 2px 0 0; color: var(--muted); font-size: 0.8rem; }

.pill {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--muted);
  white-space: nowrap;
}
.pill.ok { color: var(--accent-2); border-color: rgba(126, 231, 135, 0.35); background: rgba(126, 231, 135, 0.08); }
.pill.bad { color: var(--danger); border-color: rgba(255, 107, 107, 0.4); background: rgba(255, 107, 107, 0.08); }

.demo-banner {
  margin: 14px clamp(16px, 3vw, 36px) 0;
  padding: 12px 16px;
  border-radius: var(--radius);
  border: 1px solid rgba(255, 184, 107, 0.5);
  background: linear-gradient(90deg, rgba(255, 184, 107, 0.18), rgba(255, 184, 107, 0.05));
  color: var(--demo);
  font-weight: 700;
  letter-spacing: 0.02em;
}

.tabs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 16px clamp(16px, 3vw, 36px) 0;
  scrollbar-width: thin;
}
.tab {
  appearance: none;
  border: 1px solid transparent;
  background: transparent;
  color: var(--muted);
  padding: 10px 14px;
  border-radius: 10px 10px 0 0;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.tab:hover { color: var(--text); background: rgba(255, 255, 255, 0.03); }
.tab.active {
  color: var(--text);
  border-color: var(--line);
  border-bottom-color: var(--panel);
  background: var(--panel);
}

main { padding: 0 clamp(16px, 3vw, 36px) 34px; }

.tab-panel { display: none; padding-top: 18px; }
.tab-panel.active { display: block; animation: fade 0.16s ease-out; }
@keyframes fade { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }

.safety {
  border: 1px solid rgba(76, 194, 255, 0.28);
  background: rgba(76, 194, 255, 0.06);
  border-radius: var(--radius);
  padding: 12px 16px;
  color: #c7e8ff;
  margin-bottom: 16px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}
.card {
  background: linear-gradient(180deg, var(--panel), var(--bg-soft));
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 16px;
  box-shadow: var(--shadow);
  min-height: 92px;
}
.card span { display: block; color: var(--muted); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.09em; }
.card strong { display: block; margin-top: 6px; font-size: 1.45rem; font-variant-numeric: tabular-nums; }
.card small { display: block; margin-top: 5px; color: var(--muted); font-size: 0.72rem; }

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 18px;
  margin-bottom: 16px;
  box-shadow: var(--shadow);
}
.panel h2 { margin: 0 0 10px; font-size: 1rem; letter-spacing: 0.02em; }
.panel p { margin: 8px 0; }
.muted { color: var(--muted); }
.warning {
  color: #ffe3a3;
  border-left: 3px solid var(--warn);
  background: rgba(240, 180, 41, 0.07);
  padding: 10px 12px;
  border-radius: 8px;
}
.list { margin: 8px 0 0 18px; padding: 0; }
.list li { margin: 6px 0; }
.grid.two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }

.phase-a { border-top: 3px solid var(--accent); }
.phase-b { border-top: 3px solid var(--accent-2); }
.phase-state { font-weight: 700; font-size: 1.05rem; margin: 4px 0; }
.phase-meta { color: var(--muted); font-size: 0.85rem; }

.toolbar {
  display: flex;
  align-items: end;
  flex-wrap: wrap;
  gap: 10px;
  margin: 14px 0;
}
.field { display: grid; gap: 5px; color: var(--muted); font-size: 0.8rem; }
.field input, .field select {
  background: var(--bg-soft);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 9px 11px;
  font: inherit;
  min-width: 180px;
}
.field input:focus, .field select:focus, .button:focus-visible {
  outline: 2px solid rgba(76, 194, 255, 0.65);
  outline-offset: 1px;
}
.check { display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: 0.85rem; }
.check input { accent-color: var(--accent); }

.button {
  appearance: none;
  border: 1px solid rgba(76, 194, 255, 0.45);
  background: linear-gradient(180deg, rgba(76, 194, 255, 0.20), rgba(76, 194, 255, 0.08));
  color: var(--text);
  border-radius: 9px;
  padding: 9px 13px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.button:hover { border-color: var(--accent); background: rgba(76, 194, 255, 0.18); }
.button.secondary { border-color: var(--line); background: var(--bg-soft); color: var(--text); }
.button.secondary:hover { border-color: #3a4b61; }
.button:disabled, .button.disabled { opacity: 0.45; pointer-events: none; }
.button-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 12px; }

.table-wrap {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: auto;
  background: var(--panel);
  max-height: 62vh;
}
.data-table { width: 100%; border-collapse: collapse; min-width: 780px; }
.data-table th, .data-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(38, 51, 68, 0.7);
  text-align: left;
  white-space: nowrap;
  font-size: 0.82rem;
}
.data-table th {
  position: sticky;
  top: 0;
  background: #101823;
  color: var(--muted);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  z-index: 2;
}
.data-table tbody tr:hover { background: rgba(76, 194, 255, 0.05); }
.data-table td.mono, .mono { font-family: "Cascadia Mono", "Consolas", "SFMono-Regular", monospace; }
.empty { text-align: center; color: var(--muted); padding: 24px !important; }

.small-button {
  appearance: none;
  border: 1px solid var(--line);
  background: var(--bg-soft);
  color: var(--muted);
  border-radius: 7px;
  padding: 4px 8px;
  font: inherit;
  font-size: 0.72rem;
  cursor: pointer;
}
.small-button:hover { color: var(--text); border-color: var(--accent); }
.small-button:focus-visible { outline: 2px solid rgba(76, 194, 255, 0.65); outline-offset: 1px; }

.badge {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 1px 7px;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--muted);
}
.badge.std { color: var(--accent); border-color: rgba(76, 194, 255, 0.4); }
.badge.ext { color: #c7a6ff; border-color: rgba(199, 166, 255, 0.4); }
.badge.demo { color: var(--demo); border-color: rgba(255, 184, 107, 0.55); background: rgba(255, 184, 107, 0.08); }
.badge.err { color: var(--danger); border-color: rgba(255, 107, 107, 0.5); }

.hidden-wrap { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 0 0 10px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--line);
  background: var(--bg-soft);
  border-radius: 999px;
  padding: 3px 6px 3px 10px;
  font-size: 0.76rem;
}
.chip button {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--accent);
  font: inherit;
  cursor: pointer;
  padding: 1px 6px;
  border-radius: 999px;
}
.chip button:hover { background: rgba(76, 194, 255, 0.12); }

.compare-result .summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 10px 0 16px;
}
.summary .stat {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--bg-soft);
  padding: 8px 12px;
  font-size: 0.8rem;
  color: var(--muted);
}
.summary .stat strong { color: var(--text); font-size: 1.05rem; margin-left: 6px; }
.compare-block { margin-bottom: 18px; }
.compare-block h3 { margin: 0 0 8px; font-size: 0.9rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }
.compare-list { margin: 0; padding-left: 18px; }
.compare-list li { margin: 4px 0; }
.change-row td { background: rgba(240, 180, 41, 0.06); }
.change-detail { color: #ffd27a; font-size: 0.78rem; }
.variable { color: #c7a6ff; font-size: 0.78rem; }

.settings-grid { display: flex; flex-wrap: wrap; gap: 18px; align-items: end; margin: 10px 0; }
.code {
  background: #0a0f15;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  overflow-x: auto;
  color: #b7f7c1;
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-size: 0.82rem;
}

footer {
  padding: 18px clamp(16px, 3vw, 36px) 26px;
  color: var(--muted);
  font-size: 0.78rem;
  border-top: 1px solid var(--line);
}

.toast {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 50;
  background: #1d2938;
  color: var(--text);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  padding: 11px 14px;
  box-shadow: var(--shadow);
  max-width: min(420px, calc(100vw - 36px));
  font-size: 0.85rem;
}
.toast.error { border-left-color: var(--danger); }

.hidden { display: none !important; }

@media (max-width: 820px) {
  .grid.two { grid-template-columns: 1fr; }
  .card strong { font-size: 1.25rem; }
  .topbar { align-items: flex-start; }
  .brand-mark { width: 40px; height: 40px; }
  .data-table { min-width: 720px; }
}

@media (max-width: 520px) {
  body { font-size: 14px; }
  .toolbar { align-items: stretch; }
  .field input, .field select { min-width: 0; width: 100%; }
  .field { width: 100%; }
  .button { justify-content: center; }
}
)VCCUI";

const char VOLVO_APP_JS[] PROGMEM = R"VCCUI("use strict";

const MAX_MESSAGES = 700;
const MAX_RENDERED = 400;

const state = {
  paused: false,
  messages: [],
  lastSeq: 0,
  hidden: new Set(loadHidden()),
  filter: "",
  sortFreq: false,
  status: null,
  settingsLoaded: false,
  lastSource: null,
  lastDropped: 0,
  connected: true,
};

function $(id) { return document.getElementById(id); }

function loadHidden() {
  try {
    const raw = JSON.parse(localStorage.getItem("vcc.hidden") || "[]");
    return Array.isArray(raw) ? raw.filter((x) => typeof x === "string") : [];
  } catch (_) {
    return [];
  }
}

function saveHidden() {
  try {
    localStorage.setItem("vcc.hidden", JSON.stringify([...state.hidden]));
  } catch (_) {
    // localStorage kann in privaten Fenstern fehlen; die Liste bleibt dann nur temporaer.
  }
}

async function fetchJSON(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 6000);
  try {
    const response = await fetch(url, {
      ...options,
      cache: "no-store",
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    if (!response.ok) {
      let detail = "HTTP " + response.status;
      try {
        const body = await response.json();
        if (body && body.error) detail = body.error;
      } catch (_) { /* Antwort war kein JSON. */ }
      throw new Error(detail);
    }
    const data = await response.json();
    setOnline(true);
    return data;
  } catch (error) {
    setOnline(false);
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function setOnline(online) {
  state.connected = online;
  const el = $("connection");
  if (!el) return;
  el.classList.toggle("ok", online);
  el.classList.toggle("bad", !online);
  el.textContent = online ? "Verbunden" : "Verbindung getrennt - neuer Versuch...";
}

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function hexId(id, extended) {
  const width = extended ? 8 : 3;
  return "0x" + Number(id).toString(16).toUpperCase().padStart(width, "0");
}

function idKey(message) {
  return (message.extended ? "E:" : "S:") + Number(message.id);
}

function normalizeId(value) {
  return String(value || "").toLowerCase().replace(/^0x/, "").replace(/[^0-9a-f]/g, "");
}

function formatData(hex, dlc) {
  const s = String(hex || "").toUpperCase();
  const parts = [];
  for (let i = 0; i < Math.min(Number(dlc) || 0, 8); i += 1) {
    parts.push(s.slice(i * 2, i * 2 + 2).padEnd(2, "0"));
  }
  return parts.join(" ");
}

function formatTimestamp(us) {
  const total = Number(us) / 1e6;
  if (!Number.isFinite(total)) return "-";
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = (total % 60).toFixed(3).padStart(6, "0");
  return hours > 0 ? `${hours}:${String(minutes).padStart(2, "0")}:${seconds}` : `${String(minutes).padStart(2, "0")}:${seconds}`;
}

function formatUptime(ms) {
  const seconds = Math.floor(Number(ms) / 1000);
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
  return `${minutes}m ${secs}s`;
}

function formatFrequency(hz) {
  const value = Number(hz);
  if (!Number.isFinite(value)) return "-";
  if (value >= 100) return value.toFixed(0) + " Hz";
  if (value >= 10) return value.toFixed(1) + " Hz";
  return value.toFixed(2) + " Hz";
}

function toast(message, isError = false) {
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " error" : "");
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

function setOnlineSafe() {
  setOnline(true);
}

/* ---------- Tabs ---------- */

function initTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === button));
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
      const panel = $("tab-" + button.dataset.tab);
      if (panel) panel.classList.add("active");
      if (button.dataset.tab === "compare") refreshCompare();
      if (button.dataset.tab === "dashboard") pollStatus();
    });
  });
}

/* ---------- Status ---------- */

async function pollStatus() {
  try {
    const data = await fetchJSON("/api/status");
    state.status = data;
    renderStatus(data);
  } catch (_) {
    // Verbindungsanzeige wurde in fetchJSON aktualisiert.
  }
}

function renderStatus(data) {
  const demo = Boolean(data.demo);
  $("demo-banner").classList.toggle("hidden", !demo);
  setText("card-source", demo ? "DEMO" : "CAN");
  setText("card-source-note", demo ? "synthetische Testframes" : "passiv, LISTEN_ONLY");
  setText("card-state", data.driver_state || "-");
  setText("card-bitrate", `${data.bitrate_kbps || "-"} kbit/s`);
  setText("card-rate", `${data.msgs_per_sec ?? "-"}`);
  setText("card-total", `${data.total_frames ?? "-"}`);
  setText("card-ids", `${data.unique_ids ?? "-"}`);
  setText("card-errors", `${data.twai_errors ?? 0} / ${data.rx_queue_full ?? 0}`);
  setText("card-dropped", `${data.dropped_live ?? 0} / ${data.dropped_capture ?? 0}`);
  if (data.usb) {
    setText("card-usb", `${data.usb.tx_frames ?? 0} / ${data.usb.dropped ?? 0} / ${data.usb.tx_errors ?? 0}`);
    setText("card-usb-note", `Queue ${data.usb.queue_used ?? 0}/${data.usb.queue_capacity ?? 0} · Diag verworfen ${data.usb.diag_dropped ?? 0}`);
  }
  setText("card-ram", `${Math.round((data.free_heap || 0) / 1024)} / ${Math.round((data.free_psram || 0) / 1024)} kB`);
  setText("card-uptime", formatUptime(data.uptime_ms || 0));
  setText("card-errors-note", "TWAI-Fehler / RX-Queue voll");

  if (state.lastSource !== null && state.lastSource !== data.source) {
    state.messages = [];
    state.lastSeq = 0;
    state.lastDropped = 0;
    renderMessages();
  }
  if (state.lastSource === null) state.lastSource = data.source;
  if (Number(data.latest_seq || 0) < state.lastSeq) {
    state.messages = [];
    state.lastSeq = 0;
    renderMessages();
  }

  const a = data.phases?.a || {};
  const b = data.phases?.b || {};
  setPhase("a", a);
  setPhase("b", b);
  $("phase-a-start").disabled = Boolean(a.active || b.active);
  $("phase-b-start").disabled = Boolean(b.active || a.active);

  const recording = Boolean(data.recording);
  setText("record-status", recording ? "laeuft" : (data.capture_count > 0 ? "gestoppt" : "bereit"));
  setText("record-count", `${data.capture_count ?? 0}`);
  setText("record-capacity", `Kapazitaet: ${data.capture_capacity ?? 0}`);
  setText("record-dropped", `${data.capture_dropped ?? 0}`);
  $("record-start").disabled = recording;
  $("record-stop").disabled = !recording;
  const downloadDisabled = recording || Number(data.capture_count || 0) === 0;
  $("download-csv").classList.toggle("disabled", downloadDisabled);
  $("download-json").classList.toggle("disabled", downloadDisabled);
  $("download-csv").setAttribute("aria-disabled", String(downloadDisabled));
  $("download-json").setAttribute("aria-disabled", String(downloadDisabled));

  if (!state.settingsLoaded && data.settings) {
    $("bitrate-select").value = String(data.settings.bitrate_kbps || 500);
    $("demo-toggle").checked = Boolean(data.settings.demo);
    state.settingsLoaded = true;
  }
}

function setPhase(which, phase) {
  const prefix = "phase-" + which;
  const statusEl = $(prefix + "-state");
  const active = Boolean(phase.active);
  const valid = Boolean(phase.valid);
  if (statusEl) {
    statusEl.textContent = active ? "laeuft" : (valid ? "gestoppt (gueltig)" : "leer");
    statusEl.style.color = active ? "var(--accent-2)" : (valid ? "var(--text)" : "var(--muted)");
  }
  setText(prefix + "-frames", `${phase.frames || 0}`);
  setText(prefix + "-duration", `${((Number(phase.duration_ms) || 0) / 1000).toFixed(1)} s`);
  $(prefix + "-start").disabled = active;
  $(prefix + "-stop").disabled = !active;
}

/* ---------- Live monitor ---------- */

async function pollMessages() {
  if (state.paused) return;
  try {
    const data = await fetchJSON(`/api/messages?since=${state.lastSeq}&limit=200`);
    if (Array.isArray(data.messages) && data.messages.length > 0) {
      for (const message of data.messages) {
        state.messages.push(message);
        state.lastSeq = Math.max(state.lastSeq, Number(message.seq) || 0);
      }
      if (state.messages.length > MAX_MESSAGES) {
        state.messages.splice(0, state.messages.length - MAX_MESSAGES);
      }
      renderMessages();
    }
    if (typeof data.dropped === "number" && data.dropped !== state.lastDropped) {
      state.lastDropped = data.dropped;
      setText("monitor-dropped", `Ringpuffer: ${data.dropped} Frames ueberschrieben`);
    }
  } catch (_) {
    // fetchJSON zeigt den Verbindungsstatus.
  }
}

function renderMessages() {
  const body = $("msg-body");
  if (!body) return;
  const filter = normalizeId(state.filter);
  const rows = state.messages
    .filter((message) => {
      if (state.hidden.has(idKey(message))) return false;
      if (!filter) return true;
      const width = message.extended ? 8 : 3;
      const id = Number(message.id).toString(16).padStart(width, "0");
      return id.includes(filter);
    })
    .sort((a, b) => state.sortFreq
      ? (Number(b.freq_hz) - Number(a.freq_hz)) || (b.seq - a.seq)
      : (b.seq - a.seq))
    .slice(0, MAX_RENDERED);

  body.replaceChildren();
  if (rows.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 8;
    td.className = "empty";
    td.textContent = state.messages.length === 0
      ? "Noch keine Frames. Demo-Modus kann in den Einstellungen aktiviert werden."
      : "Keine Frames fuer diesen Filter.";
    tr.appendChild(td);
    body.appendChild(tr);
    renderHidden();
    return;
  }

  for (const message of rows) {
    const tr = document.createElement("tr");
    addCell(tr, formatTimestamp(message.timestamp_us), "mono");
    addCell(tr, hexId(message.id, message.extended), "mono");
    const typeCell = document.createElement("td");
    const typeBadge = document.createElement("span");
    typeBadge.className = "badge " + (message.extended ? "ext" : "std");
    typeBadge.textContent = message.extended ? "EXT" : "STD";
    typeCell.appendChild(typeBadge);
    tr.appendChild(typeCell);
    addCell(tr, String(message.dlc), "mono");
    addCell(tr, formatData(message.data, message.dlc), "mono");
    addCell(tr, formatFrequency(message.freq_hz), "mono");
    const sourceCell = document.createElement("td");
    const sourceBadge = document.createElement("span");
    sourceBadge.className = "badge" + (message.demo ? " demo" : "");
    sourceBadge.textContent = message.demo ? "DEMO" : "CAN";
    sourceCell.appendChild(sourceBadge);
    tr.appendChild(sourceCell);
    const actionCell = document.createElement("td");
    const hideButton = document.createElement("button");
    hideButton.type = "button";
    hideButton.className = "small-button";
    hideButton.textContent = "Ausblenden";
    hideButton.addEventListener("click", () => {
      state.hidden.add(idKey(message));
      saveHidden();
      renderMessages();
    });
    actionCell.appendChild(hideButton);
    tr.appendChild(actionCell);
    body.appendChild(tr);
  }
  renderHidden();
}

function addCell(row, text, className) {
  const td = document.createElement("td");
  if (className) td.className = className;
  td.textContent = text;
  row.appendChild(td);
}

function renderHidden() {
  const wrap = $("hidden-wrap");
  const list = $("hidden-list");
  if (!wrap || !list) return;
  list.replaceChildren();
  if (state.hidden.size === 0) {
    wrap.classList.add("hidden");
    return;
  }
  wrap.classList.remove("hidden");
  for (const key of [...state.hidden].sort()) {
    const [kind, rawId] = key.split(":");
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.appendChild(document.createTextNode(hexId(Number(rawId), kind === "E")));
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Einblenden";
    button.addEventListener("click", () => {
      state.hidden.delete(key);
      saveHidden();
      renderMessages();
    });
    chip.appendChild(button);
    list.appendChild(chip);
  }
}

async function clearMessages() {
  try {
    const data = await fetchJSON("/api/clear", { method: "POST" });
    state.messages = [];
    state.lastSeq = Number(data.latest_seq || 0);
    state.lastDropped = 0;
    setText("monitor-dropped", "");
    renderMessages();
    toast("Live-Liste geloescht.");
  } catch (error) {
    toast("Loeschen fehlgeschlagen: " + error.message, true);
  }
}

/* ---------- Signal comparison ---------- */

async function phaseAction(phase, action) {
  try {
    const data = await fetchJSON("/api/phase", {
      method: "POST",
      body: JSON.stringify({ phase, action }),
    });
    if (!data.ok) throw new Error(data.error || "Aktion nicht moeglich");
    toast(action === "start" ? `Phase ${phase} gestartet.` : `Phase ${phase} gestoppt.`);
    await pollStatus();
    await refreshCompare();
  } catch (error) {
    toast("Phase " + phase + ": " + error.message, true);
  }
}

async function resetPhases() {
  try {
    const data = await fetchJSON("/api/phase", {
      method: "POST",
      body: JSON.stringify({ action: "reset" }),
    });
    if (!data.ok) throw new Error(data.error || "Zuruecksetzen fehlgeschlagen");
    toast("Phasen zurueckgesetzt.");
    await pollStatus();
    await refreshCompare();
  } catch (error) {
    toast(error.message, true);
  }
}

async function refreshCompare() {
  try {
    const data = await fetchJSON("/api/compare");
    renderCompare(data);
  } catch (_) {
    // Verbindungsanzeige reicht.
  }
}

function renderCompare(data) {
  const container = $("compare-result");
  if (!container) return;
  container.replaceChildren();
  if (!data.ok) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Phase A und B starten/stoppen, dann den Vergleich aktualisieren.";
    container.appendChild(p);
    return;
  }

  if (data.demo) {
    const demo = document.createElement("div");
    demo.className = "demo-banner";
    demo.textContent = "DEMO: Dieser Vergleich enthaelt synthetische Frames, keine Fahrzeugdaten.";
    container.appendChild(demo);
  }

  const entries = Array.isArray(data.entries) ? data.entries : [];
  const newIds = entries.filter((entry) => entry.in_b && !entry.in_a);
  const missingIds = entries.filter((entry) => entry.in_a && !entry.in_b);
  const common = entries.filter((entry) => entry.in_a && entry.in_b);
  const changed = common.filter((entry) => entry.payload_changed || entry.frequency_changed);

  const summary = document.createElement("div");
  summary.className = "summary";
  addStat(summary, "Dauer A", ((Number(data.duration_a_ms) || 0) / 1000).toFixed(1) + " s");
  addStat(summary, "Dauer B", ((Number(data.duration_b_ms) || 0) / 1000).toFixed(1) + " s");
  addStat(summary, "Neu in B", String(newIds.length));
  addStat(summary, "Nur in A", String(missingIds.length));
  addStat(summary, "Gemeinsam", String(common.length));
  addStat(summary, "Mit Aenderung", String(changed.length));
  container.appendChild(summary);

  if (data.truncated) {
    const note = document.createElement("p");
    note.className = "warning";
    note.textContent = "Die Ergebnisliste wurde gekuerzt. Bitte Phase kuerzer halten oder Filter verwenden.";
    container.appendChild(note);
  }

  container.appendChild(buildIdList("Neu in Phase B", newIds, "b"));
  container.appendChild(buildIdList("Nur in Phase A vorhanden", missingIds, "a"));
  container.appendChild(buildChangeTable(changed));

  const hint = document.createElement("p");
  hint.className = "muted";
  hint.textContent = "Keine automatische Bedeutung: IDs und Bits muessen experimentell verifiziert werden. Frequenzaenderungen werden ab 20 % und 0,2 Hz markiert.";
  container.appendChild(hint);
}

function addStat(parent, label, value) {
  const div = document.createElement("div");
  div.className = "stat";
  div.appendChild(document.createTextNode(label));
  const strong = document.createElement("strong");
  strong.textContent = value;
  div.appendChild(strong);
  parent.appendChild(div);
}

function buildIdList(title, entries, phase) {
  const block = document.createElement("section");
  block.className = "compare-block";
  const h = document.createElement("h3");
  h.textContent = title;
  block.appendChild(h);
  if (entries.length === 0) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Keine IDs.";
    block.appendChild(p);
    return block;
  }
  const list = document.createElement("ul");
  list.className = "compare-list";
  for (const entry of entries.slice(0, 100)) {
    const li = document.createElement("li");
    const count = phase === "a" ? entry.count_a : entry.count_b;
    const freq = phase === "a" ? entry.freq_a : entry.freq_b;
    li.textContent = `${entry.id_hex} - ${count} Frames, ${formatFrequency(freq)}`;
    if (entry.demo) {
      const badge = document.createElement("span");
      badge.className = "badge demo";
      badge.textContent = "DEMO";
      li.appendChild(document.createTextNode(" "));
      li.appendChild(badge);
    }
    list.appendChild(li);
  }
  block.appendChild(list);
  return block;
}

function buildChangeTable(entries) {
  const block = document.createElement("section");
  block.className = "compare-block";
  const h = document.createElement("h3");
  h.textContent = "Gemeinsame IDs mit Aenderungen";
  block.appendChild(h);
  if (entries.length === 0) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Keine Daten- oder Frequenzaenderungen erkannt.";
    block.appendChild(p);
    return block;
  }

  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  const table = document.createElement("table");
  table.className = "data-table";
  const thead = document.createElement("thead");
  const header = document.createElement("tr");
  ["CAN-ID", "Daten A", "Daten B", "Aenderungen", "Frequenz A", "Frequenz B", "Delta"].forEach((text) => {
    const th = document.createElement("th");
    th.textContent = text;
    header.appendChild(th);
  });
  thead.appendChild(header);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");

  for (const entry of entries) {
    const tr = document.createElement("tr");
    tr.className = "change-row";
    addCell(tr, entry.id_hex, "mono");
    addCell(tr, formatData(entry.data_a, entry.dlc_a), "mono");
    addCell(tr, formatData(entry.data_b, entry.dlc_b), "mono");
    const changeCell = document.createElement("td");
    const details = [];
    for (const change of entry.changed_bytes || []) {
      const xor = parseInt(change.xor, 16) || 0;
      const bits = [];
      for (let bit = 0; bit < 8; bit += 1) {
        if (xor & (1 << bit)) bits.push(bit);
      }
      const bitText = bits.length ? `, Bits ${bits.join(",")}` : "";
      details.push(`Byte ${change.index}: ${change.a} -> ${change.b} (XOR ${change.xor}${bitText})`);
    }
    if (entry.frequency_changed) details.push("Frequenz geaendert");
    const detailSpan = document.createElement("span");
    detailSpan.className = "change-detail";
    detailSpan.textContent = details.length ? details.join("; ") : "Daten unveraendert";
    changeCell.appendChild(detailSpan);
    if (entry.variable_a?.some((value) => value !== "00") || entry.variable_b?.some((value) => value !== "00")) {
      const variable = document.createElement("div");
      variable.className = "variable";
      variable.textContent = `Variabel A: ${compactBytes(entry.variable_a)} | B: ${compactBytes(entry.variable_b)}`;
      changeCell.appendChild(variable);
    }
    tr.appendChild(changeCell);
    addCell(tr, formatFrequency(entry.freq_a), "mono");
    addCell(tr, formatFrequency(entry.freq_b), "mono");
    const delta = Number(entry.freq_delta_pct);
    addCell(tr, Number.isFinite(delta) ? `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} %` : "-", "mono");
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  block.appendChild(wrap);
  return block;
}

function compactBytes(values) {
  if (!Array.isArray(values)) return "-";
  return values.map((value, index) => `${index}:${String(value).toUpperCase()}`).join(" ");
}

/* ---------- Recording ---------- */

async function recordAction(action) {
  try {
    const data = await fetchJSON("/api/record", {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    if (!data.ok) throw new Error(data.error || "Aktion nicht moeglich");
    toast(action === "start" ? "Aufzeichnung gestartet." : "Aufzeichnung gestoppt.");
    await pollStatus();
  } catch (error) {
    toast("Aufzeichnung: " + error.message, true);
  }
}

/* ---------- Settings ---------- */

async function saveSettings() {
  const bitrate = Number($("bitrate-select").value);
  const demo = Boolean($("demo-toggle").checked);
  try {
    const data = await fetchJSON("/api/settings", {
      method: "POST",
      body: JSON.stringify({ bitrate, demo }),
    });
    if (!data.ok) throw new Error(data.error || "Speichern fehlgeschlagen");
    $("settings-status").textContent = "Gespeichert. CAN bleibt aus; START ist bis zur Hardwarefreigabe gesperrt.";
    state.settingsLoaded = false;
    state.messages = [];
    state.lastSeq = 0;
    state.lastDropped = 0;
    renderMessages();
    await pollStatus();
    toast("Einstellungen gespeichert. CAN bleibt aus; START ist gesperrt.");
  } catch (error) {
    $("settings-status").textContent = "Fehler: " + error.message;
    toast("Einstellungen: " + error.message, true);
  }
}

/* ---------- Initialisierung ---------- */

function init() {
  initTabs();

  $("filter-id").addEventListener("input", (event) => {
    state.filter = event.target.value;
    renderMessages();
  });
  $("btn-pause").addEventListener("click", () => {
    state.paused = !state.paused;
    $("btn-pause").textContent = state.paused ? "Fortsetzen" : "Pausieren";
    toast(state.paused ? "Live-Anzeige pausiert." : "Live-Anzeige fortgesetzt.");
    if (!state.paused) pollMessages();
  });
  $("btn-clear").addEventListener("click", clearMessages);
  $("sort-freq").addEventListener("change", (event) => {
    state.sortFreq = event.target.checked;
    renderMessages();
  });

  $("phase-a-start").addEventListener("click", () => phaseAction("A", "start"));
  $("phase-a-stop").addEventListener("click", () => phaseAction("A", "stop"));
  $("phase-b-start").addEventListener("click", () => phaseAction("B", "start"));
  $("phase-b-stop").addEventListener("click", () => phaseAction("B", "stop"));
  $("compare-refresh").addEventListener("click", refreshCompare);
  $("compare-reset").addEventListener("click", resetPhases);

  $("record-start").addEventListener("click", () => recordAction("start"));
  $("record-stop").addEventListener("click", () => recordAction("stop"));
  $("download-csv").addEventListener("click", (event) => {
    if ($("download-csv").classList.contains("disabled")) event.preventDefault();
  });
  $("download-json").addEventListener("click", (event) => {
    if ($("download-json").classList.contains("disabled")) event.preventDefault();
  });

  $("btn-save-settings").addEventListener("click", saveSettings);

  renderMessages();
  renderHidden();
  pollStatus();
  pollMessages();
  setInterval(pollStatus, 1000);
  setInterval(() => { if (!state.paused) pollMessages(); }, 400);
  setInterval(() => { if ($("tab-compare").classList.contains("active")) refreshCompare(); }, 3000);
}

document.addEventListener("DOMContentLoaded", init);
)VCCUI";
