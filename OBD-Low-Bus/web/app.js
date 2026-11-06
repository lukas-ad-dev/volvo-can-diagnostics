"use strict";

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
    $("settings-status").textContent = "Gespeichert. Quelle wird neu gestartet.";
    state.settingsLoaded = false;
    state.messages = [];
    state.lastSeq = 0;
    state.lastDropped = 0;
    renderMessages();
    await pollStatus();
    toast("Einstellungen gespeichert; Live-Daten wurden zurueckgesetzt.");
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
