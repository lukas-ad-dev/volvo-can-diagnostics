"use strict";

const state = {
  status: null,
  signals: [],
  references: null,
  assistant: null,
  scenarios: {},
  events: [],
  lastEventId: 0,
  selectedSignal: null,
  editorSignalId: null,
  scenariosLoaded: false,
  monitorFrames: [],
  monitorLastSeq: 0,
  monitorRates: new Map(),
  monitorPaused: false,
  monitorBusy: false,
  monitorMissed: 0,
  monitorStatus: null,
  assistantChoices: {},
};

let assistantSelectActive = false;

function $(id) { return document.getElementById(id); }

function text(id, value) { const el = $(id); if (el) el.textContent = value; }
function show(id, visible) { const el = $(id); if (el) el.classList.toggle("hidden", !visible); }

async function api(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let data = {};
  try { data = await response.json(); } catch (_) { /* leer */ }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || ("HTTP " + response.status));
  }
  return data;
}

function toast(message, error = false) {
  const el = document.createElement("div");
  el.className = "toast" + (error ? " error" : "");
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

function fmtFrequency(hz) {
  const value = Number(hz);
  if (!Number.isFinite(value) || value <= 0) return "-";
  if (value >= 100) return value.toFixed(0) + " Hz";
  if (value >= 10) return value.toFixed(1) + " Hz";
  return value.toFixed(2) + " Hz";
}

function fmtAge(ms) {
  if (ms === null || ms === undefined) return "-";
  if (ms < 1000) return Math.round(ms) + " ms";
  if (ms < 60000) return (ms / 1000).toFixed(1) + " s";
  return (ms / 60000).toFixed(1) + " min";
}

function fmtTime(iso) {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleTimeString("de-DE", { hour12: false }) + "." + String(date.getMilliseconds()).padStart(3, "0");
}

function statusLabel(status) {
  return ({ unknown: "UNBEKANNT", candidate: "KANDIDAT", testing: "IN PRUEFUNG", confirmed: "BESTAETIGT", rejected: "VERWORFEN" })[status] || status;
}

function valueText(signal) {
  if (signal.kind === "bus") return signal.state_text || "-";
  if (signal.kind === "value") {
    const value = signal.display_value;
    if (value === null || value === undefined) return "-";
    return `${Number(value).toFixed(1)} ${signal.unit || ""}`.trim();
  }
  return signal.state_text || "-";
}

function rawHint(signal) {
  if (signal.kind === "bus") return "";
  if (signal.can_id === null || signal.can_id === undefined) return "nicht zugeordnet";
  if (signal.unknown && signal.raw_value !== null && signal.raw_value !== undefined) {
    return `Roh: ${signal.active ? "EIN" : "AUS"} (unbestaetigt)`;
  }
  return "";
}

function tabTo(name) {
  document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
  const panel = $("tab-" + name);
  if (panel) panel.classList.add("active");
  if (name === "monitor") pollMonitor(true);
  if (name === "assistant") pollAssistant();
  if (name === "references") loadReferences();
  if (name === "export") { pollStatus(); refreshExportFiles(); pollRawFrames(); }
  if (name === "live") {
    if (!state.selectedSignal && state.signals[0]) state.selectedSignal = state.signals[0].id;
    renderLive();
    renderTimeline();
  }
  if (name === "editor" && !state.editorSignalId && state.signals[0]) {
    state.editorSignalId = state.signals[0].id;
    populateEditor();
  }
}

function initTabs() {
  document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => tabTo(button.dataset.tab)));
}

/* ---------- Status / Signale ---------- */

async function pollStatus() {
  try {
    const status = await api("/api/status");
    state.status = status;
    renderStatus(status);
  } catch (error) {
    text("hint-banner", "Diagnoseserver nicht erreichbar: " + error.message);
    show("hint-banner", true);
  }
}

function renderStatus(status) {
  text("profile-pill", status.profile || "-");
  document.title = "Volvo CAN Signalerkennung - " + (status.profile || "Volvo");
  text("source-pill", status.source === "demo" ? "DEMO-Quelle" : "USB-CDC");
  $("source-pill").className = "pill " + (status.source === "demo" ? "demo" : "ok");
  text("connection-pill", status.connected ? "USB verbunden" : (status.source === "demo" ? "Demo" : "USB getrennt"));
  $("connection-pill").className = "pill " + (status.connected || status.source === "demo" ? "ok" : "bad");
  text("demo-pill", "DEMO");
  show("demo-pill", status.demo_mode);
  show("demo-banner", status.demo_mode);
  const fw = status.firmware_can || {};
  const canState = fw.can_state || (fw.twai_installed ? fw.twai_state_name : "STOP");
  const canActive = canState === "ARMED" || canState === "RUNNING";
  text("can-pill", "CAN: " + (canState || "-"));
  $("can-pill").className = "pill " + (canState === "BUS_OFF" ? "bad" : canActive ? "demo" : "ok");
  text("bitrate-pill", "Bitrate: " + (fw.bitrate_kbps ? fw.bitrate_kbps + " kbit/s" : "-"));
  $("bitrate-pill").className = "pill " + (fw.bitrate_kbps === 500 ? "ok" : "bad");
  text("twai-pill", "TWAI: " + (fw.twai_installed ? (fw.twai_state_name || "installiert") : "disabled"));
  $("twai-pill").className = "pill " + (fw.twai_installed ? "demo" : "ok");
  text("start-pill", fw.start_locked === false ? "START: FREI" : "START: GESPERRT");
  $("start-pill").className = "pill " + (fw.start_locked === false ? "demo" : "bad");
  const canRunning = Boolean(fw.can_armed || fw.twai_installed);
  $("can-start").disabled = canRunning;
  $("can-stop").disabled = !canRunning;
  text("can-status-text", (canState || "-") + " / " + (fw.listen_only ? "LISTEN_ONLY" : "-"));
  text("can-alerts", fw.alerts === undefined ? "-" : "0x" + Number(fw.alerts).toString(16).toUpperCase());
  text("fw-updated", fw.updated_iso ? fmtTime(fw.updated_iso) : "-");
  if (fw.start_locked !== undefined) {
    text("safety-banner", fw.start_locked
      ? "NUR LESEN: ausschliesslich passiv empfangen. Keine CAN-Frames senden. Fester Testbetrieb 500 kbit/s; START ist gesperrt. Kein Bitratenscan, kein Serverstart ohne Freigabe."
      : "NUR LESEN: ausschliesslich passiv empfangen. Keine CAN-Frames senden. Fester Testbetrieb 500 kbit/s; START ist freigegeben.");
  }
  if (status.demo_mode) text("session-name", status.session.stem + " (DEMO)");
  else text("session-name", status.session.stem);
  text("measurement-name", status.measurement.active ? status.measurement.name : "-");
  text("frame-count", String(status.counters.frames_received));
  text("last-frame", status.last_frame.received_iso ? fmtTime(status.last_frame.received_iso) : "-");
  if (status.no_frames_hint) {
    text("hint-banner", status.no_frames_hint);
    show("hint-banner", true);
  } else {
    show("hint-banner", false);
  }
  $("measurement-start").disabled = status.measurement.active;
  $("measurement-stop").disabled = !status.measurement.active;
  if (status.source === "demo") {
    $("demo-toggle").disabled = false;
  }
  if (!state.scenariosLoaded) loadScenarios();
  if ($("tab-export").classList.contains("active")) renderExportStatus(status);
}

async function pollSignals() {
  try {
    const data = await api("/api/signals");
    state.signals = data.signals || [];
    renderSignals();
    renderSignalSelectors();
    if (state.selectedSignal) renderLive();
    if (state.editorSignalId) renderConfirmSummary();
  } catch (_) { /* Status zeigt Fehler */ }
}

function renderSignals() {
  const grid = $("signal-grid");
  grid.replaceChildren();
  for (const signal of state.signals) {
    const card = document.createElement("article");
    card.className = "signal-card" + (signal.unknown ? " unknown" : "") + (signal.stale ? " stale" : "");
    const head = document.createElement("div");
    head.className = "signal-head";
    const titleWrap = document.createElement("div");
    const name = document.createElement("div");
    name.className = "signal-name";
    name.textContent = signal.name;
    const sub = document.createElement("div");
    sub.className = "muted small";
    sub.textContent = signal.id_hex ? `${signal.id_hex} · ${signal.extended ? "EXT" : "STD"}` : "nicht zugeordnet";
    titleWrap.append(name, sub);
    const led = document.createElement("span");
    led.className = "led " + signal.led;
    led.title = signal.state_text;
    head.append(titleWrap, led);
    card.appendChild(head);

    const stateEl = document.createElement("div");
    stateEl.className = "signal-state";
    stateEl.style.color = signal.led === "green" ? "var(--green)" : signal.led === "red" ? "var(--red)" : signal.led === "yellow" ? "var(--yellow)" : "var(--muted)";
    stateEl.textContent = signal.state_text;
    card.appendChild(stateEl);

    if (signal.kind === "value") {
      const value = document.createElement("div");
      value.className = "signal-value";
      value.textContent = valueText(signal);
      card.appendChild(value);
    }

    const meta = document.createElement("div");
    meta.className = "signal-meta";
    const addMeta = (key, value) => {
      const k = document.createElement("span"); k.textContent = key;
      const v = document.createElement("b"); v.textContent = value;
      meta.append(k, v);
    };
    addMeta("Byte / Maske", signal.byte === null ? "-" : `Byte ${signal.byte} · 0x${Number(signal.bit_mask).toString(16).toUpperCase()}`);
    addMeta("Letzte Aktualisierung", signal.last_update ? `${fmtTime(signal.last_update)} (${fmtAge(signal.age_ms)})` : "-");
    addMeta("Empfang", fmtFrequency(signal.freq_hz));
    addMeta("Vertrauen", statusLabel(signal.status));
    addMeta("Messungen", (signal.measurements || []).length ? signal.measurements.slice(-3).join(", ") : "-");
    addMeta("Evidenz", `${signal.evidence_count || 0} Laeufe${signal.demo ? " · DEMO" : ""}`);
    card.appendChild(meta);

    const hint = rawHint(signal);
    if (hint) {
      const hintEl = document.createElement("div");
      hintEl.className = "muted small";
      hintEl.textContent = hint;
      card.appendChild(hintEl);
    }

    const actions = document.createElement("div");
    actions.className = "signal-actions";
    const edit = document.createElement("button");
    edit.className = "button small secondary"; edit.type = "button"; edit.textContent = "Bearbeiten";
    edit.addEventListener("click", () => { state.editorSignalId = signal.id; tabTo("editor"); populateEditor(); });
    const live = document.createElement("button");
    live.className = "button small secondary"; live.type = "button"; live.textContent = "Live-Test";
    live.addEventListener("click", () => { state.selectedSignal = signal.id; tabTo("live"); renderLive(); });
    actions.append(edit, live);
    card.appendChild(actions);
    grid.appendChild(card);
  }
}

function renderSignalSelectors() {
  for (const id of ["live-signal", "editor-select"]) {
    const select = $(id);
    if (!select) continue;
    const current = id === "live-signal" ? state.selectedSignal : state.editorSignalId;
    select.replaceChildren();
    for (const signal of state.signals) {
      const option = document.createElement("option");
      option.value = signal.id;
      option.textContent = `${signal.name}${signal.id_hex ? " · " + signal.id_hex : ""}`;
      select.appendChild(option);
    }
    if (current) select.value = current;
  }
}

/* ---------- Live / Timeline ---------- */

function renderLive() {
  const select = $("live-signal");
  const signal = state.signals.find((item) => item.id === (state.selectedSignal || select.value));
  if (!signal) {
    $("live-card").textContent = "Noch kein Signal ausgewaehlt.";
    return;
  }
  state.selectedSignal = signal.id;
  select.value = signal.id;
  const card = $("live-card");
  card.replaceChildren();
  const led = document.createElement("span"); led.className = "led " + signal.led;
  const title = document.createElement("span"); title.style.fontWeight = "800"; title.style.marginLeft = "6px"; title.textContent = signal.name;
  const stateEl = document.createElement("div"); stateEl.className = "live-state"; stateEl.textContent = signal.state_text;
  stateEl.style.color = signal.led === "green" ? "var(--green)" : signal.led === "red" ? "var(--red)" : signal.led === "yellow" ? "var(--yellow)" : "var(--muted)";
  const value = document.createElement("div"); value.textContent = signal.kind === "value" ? valueText(signal) : (signal.active ? "EIN" : "AUS");
  const meta = document.createElement("div"); meta.className = "muted small";
  meta.textContent = `${signal.id_hex || "nicht zugeordnet"} · ${signal.extended ? "EXT" : "STD"} · Byte ${signal.byte ?? "-"} / 0x${Number(signal.bit_mask).toString(16).toUpperCase()} · ${fmtFrequency(signal.freq_hz)} · ${statusLabel(signal.status)}`;
  card.append(led, title, stateEl, value, meta);

  const history = state.events
    .filter((event) => event.signal_id === signal.id && (event.kind === "signal_change" || event.kind === "signal_state"))
    .slice(-20)
    .reverse();
  const historyEl = document.createElement("div");
  historyEl.className = "timeline";
  if (history.length === 0) {
    const empty = document.createElement("div"); empty.className = "timeline-entry muted"; empty.textContent = "Noch keine Zustandswechsel beobachtet.";
    historyEl.appendChild(empty);
  }
  for (const event of history) {
    const entry = document.createElement("div");
    entry.className = "timeline-entry signal_change";
    entry.textContent = `${fmtTime(event.timestamp)}  P: ${event.from || "-"}  →  R: ${event.to || event.text || "-"}${event.measurement ? "  [" + event.measurement + "]" : ""}`;
    historyEl.appendChild(entry);
  }
  card.appendChild(historyEl);
}

function renderTimeline() {
  const list = $("timeline");
  list.replaceChildren();
  const events = state.events.slice(-200).reverse();
  if (events.length === 0) {
    const empty = document.createElement("div"); empty.className = "timeline-entry muted"; empty.textContent = "Noch keine Ereignisse.";
    list.appendChild(empty);
    return;
  }
  for (const event of events) {
    const entry = document.createElement("div");
    entry.className = "timeline-entry " + event.kind;
    const time = document.createElement("span"); time.className = "timeline-time"; time.textContent = fmtTime(event.timestamp) + "  ";
    const textEl = document.createElement("span");
    let message = "";
    switch (event.kind) {
      case "user": message = "BENUTZER: " + (event.label || ""); break;
      case "signal_change": message = `${event.signal_id}: ${event.from} → ${event.to}`; break;
      case "signal_state": message = `${event.signal_id}: ${event.text || ""} (${event.from} → ${event.to})`; break;
      case "connection": message = event.message || "USB-Verbindung"; break;
      case "measurement_start": message = "Messung gestartet: " + event.name; break;
      case "measurement_stop": message = "Messung gestoppt: " + event.name; break;
      case "assistant_start": message = "Assistent gestartet: " + (event.action_label || "-"); break;
      case "assistant_action": message = "Aktion markiert: " + (event.action_label || "-"); break;
      case "assistant_evaluate": message = "Assistent ausgewertet: " + (event.candidates ?? 0) + " Kandidaten"; break;
      case "assistant_bind": message = "Kandidat gebunden: " + event.signal_id; break;
      case "measurement": message = event.message || ""; break;
      case "demo_action": message = "DEMO-Aktion: " + event.value; break;
      case "firmware_stats": message = "ESP " + (event.message || ""); break;
      default: message = event.message || event.label || event.kind;
    }
    textEl.textContent = message;
    entry.append(time, textEl);
    list.appendChild(entry);
  }
}

async function pollEvents() {
  try {
    const data = await api(`/api/events?since=${state.lastEventId}`);
    if (data.events?.length) {
      for (const event of data.events) {
        state.events.push(event);
        state.lastEventId = Math.max(state.lastEventId, Number(event.id) || 0);
      }
      if (state.events.length > 1200) state.events.splice(0, state.events.length - 1200);
      renderTimeline();
      if ($("tab-live").classList.contains("active")) renderLive();
    }
  } catch (_) { /* Status zeigt Fehler */ }
}

/* ---------- Assistent ---------- */

async function loadScenarios() {
  try {
    const data = await api("/api/assistant");
    state.scenarios = data.scenarios || {};
    state.scenariosLoaded = true;
    const select = $("measurement-select");
    select.replaceChildren();
    for (const [key, entry] of Object.entries(state.scenarios)) {
      const option = document.createElement("option");
      option.value = entry[0];
      option.textContent = `${key}: ${entry[1]}`;
      select.appendChild(option);
    }
  } catch (_) { /* spaeter erneut */ }
}

async function pollAssistant() {
  if (assistantSelectActive) return;
  try {
    const data = await api("/api/assistant");
    state.assistant = data.assistant;
    if (!state.scenariosLoaded && data.scenarios) {
      state.scenarios = data.scenarios;
      loadScenarios();
    }
    renderAssistant(state.assistant);
  } catch (_) { /* Status zeigt Fehler */ }
}

function renderAssistant(data) {
  if (!data) return;
  const phaseNames = {
    idle: "Bereit",
    baseline: "Grundzustand: Aktion AUS lassen",
    waiting_action: "Jetzt Aktion EINschalten und markieren",
    action1: "Aktion EIN lassen",
    waiting_off: "Jetzt Aktion AUSschalten und markieren",
    recovery: "Aktion AUS lassen",
    waiting_action2: "Jetzt Aktion erneut EINschalten und markieren",
    action2: "Aktion EIN lassen (2. Zyklus)",
    ready: "Auswertung bereit",
    evaluated: "Ausgewertet",
  };
  const phase = phaseNames[data.phase] || data.phase;
  const timedPhases = new Set(["baseline", "action1", "recovery", "action2"]);
  const remaining = timedPhases.has(data.phase) ? ` · ${data.remaining_seconds.toFixed(1)} s` : "";
  $("assistant-status").innerHTML = "";
  const strong = document.createElement("strong"); strong.textContent = phase + remaining;
  const info = document.createElement("span");
  info.textContent = ` · A: ${data.baseline_frames} F / ${data.baseline_ids} IDs · B1: ${data.action1_frames} F / ${data.action1_ids} IDs · AUS: ${data.recovery_frames} F / ${data.recovery_ids} IDs · B2: ${data.action2_frames} F / ${data.action2_ids} IDs · Aktion: ${data.action_label || "-"} · Lauf: ${data.run_id || "-"}`;
  $("assistant-status").append(strong, info);
  $("assistant-start").disabled = !(data.phase === "idle" || data.phase === "evaluated");
  const markLabels = {
    waiting_action: "Aktion EIN markieren",
    waiting_off: "Aktion AUS markieren",
    waiting_action2: "Aktion EIN (2) markieren",
  };
  $("assistant-mark").disabled = !Object.prototype.hasOwnProperty.call(markLabels, data.phase);
  $("assistant-mark").textContent = markLabels[data.phase] || "Aktion markieren";
  $("assistant-evaluate").disabled = data.phase !== "ready";
  $("assistant-reset").disabled = data.phase === "idle";

  const container = $("assistant-candidates");
  container.replaceChildren();
  if (data.phase === "evaluated") {
    const summary = document.createElement("div");
    summary.className = "muted small";
    summary.textContent = `Neu in B: ${data.new_ids.length} · Nur in A: ${data.missing_ids.length} · Kandidatenbits: ${data.candidates.length}`;
    container.appendChild(summary);
    for (const [index, candidate] of data.candidates.entries()) {
      const box = document.createElement("div");
      box.className = "candidate";
      const head = document.createElement("div");
      head.className = "candidate-head";
      const title = document.createElement("div");
      title.innerHTML = `<code>${candidate.id_hex}</code> · Byte ${candidate.byte} · Bit ${candidate.bit} · Maske 0x${Number(candidate.mask).toString(16).toUpperCase()} · A=${candidate.a_value} B=${candidate.b_value}`;
      const score = document.createElement("span");
      score.className = "badge"; score.textContent = "Score " + candidate.score + (candidate.demo ? " · DEMO" : "");
      const live = document.createElement("span");
      const liveValue = candidate.live_value;
      live.className = "badge " + (liveValue === 1 ? "live-on" : liveValue === 0 ? "live-off" : "live-unknown");
      live.textContent = liveValue === 1 ? "LIVE EIN" : liveValue === 0 ? "LIVE AUS" : "LIVE ?";
      if (candidate.live_age_ms !== null && candidate.live_age_ms !== undefined) {
        live.title = `Letzter Frame: ${candidate.live_age_ms} ms`;
      }
      head.append(title, score, live);
      box.appendChild(head);
      if (candidate.warnings?.length) {
        const warn = document.createElement("div"); warn.className = "warnings"; warn.textContent = "Hinweise: " + candidate.warnings.join(" · ");
        box.appendChild(warn);
      }
      const bind = document.createElement("div");
      bind.className = "bind";
      const candidateKey = `${candidate.id_hex}:${candidate.byte}:${candidate.bit}`;
      const select = document.createElement("select");
      for (const signal of state.signals) {
        const option = document.createElement("option");
        option.value = signal.id;
        option.textContent = signal.name;
        select.appendChild(option);
      }
      const savedChoice = state.assistantChoices[candidateKey];
      if (savedChoice) select.value = savedChoice;
      else if (state.selectedSignal) select.value = state.selectedSignal;
      select.addEventListener("focus", () => { assistantSelectActive = true; });
      select.addEventListener("change", () => {
        state.assistantChoices[candidateKey] = select.value;
        state.selectedSignal = select.value;
      });
      select.addEventListener("blur", () => {
        assistantSelectActive = false;
        pollAssistant();
      });
      const button = document.createElement("button");
      button.className = "button small"; button.type = "button"; button.textContent = "An Kachel binden";
      button.addEventListener("click", async () => {
        const chosen = select.value;
        try {
          await api("/api/assistant/bind", { method: "POST", body: JSON.stringify({ signal_id: chosen, candidate_index: index }) });
          state.selectedSignal = chosen;
          state.editorSignalId = chosen;
          state.assistantChoices[candidateKey] = chosen;
          toast("Kandidat an '" + chosen + "' gebunden. Bitte Gegenaktion und Wiederholungen durchfuehren.");
          await pollSignals();
        } catch (error) { toast(error.message, true); }
      });
      bind.append(select, button);
      box.appendChild(bind);
      container.appendChild(box);
    }
    if (data.new_ids.length || data.missing_ids.length) {
      const ids = document.createElement("div");
      ids.className = "muted small";
      ids.textContent = "IDs nur in einer Phase: " +
        [...data.new_ids.map((item) => item.id_hex + " (B)"), ...data.missing_ids.map((item) => item.id_hex + " (A)")].join(", ");
      container.appendChild(ids);
    }
  }
}

async function assistantAction(path, payload = {}) {
  if (path.endsWith("/start") || path.endsWith("/reset") || path.endsWith("/evaluate")) {
    state.assistantChoices = {};
  }
  try {
    const data = await api(path, { method: "POST", body: JSON.stringify(payload) });
    state.assistant = data.assistant || data;
    renderAssistant(state.assistant);
    await pollSignals();
  } catch (error) { toast(error.message, true); }
}

/* ---------- Editor / Bestaetigung ---------- */

function populateEditor() {
  const signal = state.signals.find((item) => item.id === state.editorSignalId) || state.signals[0];
  if (!signal) return;
  state.editorSignalId = signal.id;
  $("editor-select").value = signal.id;
  $("editor-name").value = signal.name || "";
  $("editor-kind").value = signal.kind || "bool";
  $("editor-unit").value = signal.unit || "";
  $("editor-can-id").value = signal.can_id === null || signal.can_id === undefined ? "" : "0x" + Number(signal.can_id).toString(16).toUpperCase();
  $("editor-extended").value = String(Boolean(signal.extended));
  $("editor-dlc").value = signal.dlc || 8;
  $("editor-byte").value = signal.byte === null || signal.byte === undefined ? 0 : signal.byte;
  $("editor-length").value = signal.length || 1;
  $("editor-endianness").value = signal.endianness || "little";
  $("editor-mask").value = "0x" + Number(signal.bit_mask || 1).toString(16).toUpperCase();
  $("editor-compare").value = signal.compare_value === null || signal.compare_value === undefined ? "" : String(signal.compare_value);
  $("editor-invert").checked = Boolean(signal.invert);
  $("editor-timeout").value = signal.timeout_ms || 2000;
  $("editor-min").value = signal.value_min ?? "";
  $("editor-max").value = signal.value_max ?? "";
  $("editor-factor").value = signal.factor ?? 1;
  $("editor-offset").value = signal.offset ?? 0;
  $("editor-notes").value = signal.notes || "";
  renderConfirmSummary();
}

async function saveEditor() {
  const signal = state.signals.find((item) => item.id === state.editorSignalId);
  if (!signal) return;
  const payload = {
    ...signal,
    name: $("editor-name").value,
    kind: $("editor-kind").value,
    unit: $("editor-unit").value,
    can_id: $("editor-can-id").value.trim() || null,
    extended: $("editor-extended").value === "true",
    dlc: Number($("editor-dlc").value),
    byte: $("editor-byte").value === "" ? null : Number($("editor-byte").value),
    length: Number($("editor-length").value),
    endianness: $("editor-endianness").value,
    bit_mask: $("editor-mask").value,
    compare_value: $("editor-compare").value.trim() || null,
    invert: $("editor-invert").checked,
    timeout_ms: Number($("editor-timeout").value),
    value_min: $("editor-min").value === "" ? null : Number($("editor-min").value),
    value_max: $("editor-max").value === "" ? null : Number($("editor-max").value),
    factor: Number($("editor-factor").value || 1),
    offset: Number($("editor-offset").value || 0),
    notes: $("editor-notes").value,
  };
  try {
    const saved = await api("/api/signals", { method: "POST", body: JSON.stringify(payload) });
    text("editor-status", "Gespeichert. Status: " + statusLabel(saved.status));
    toast("Signaldefinition gespeichert.");
    await pollSignals();
    state.editorSignalId = saved.id;
    populateEditor();
  } catch (error) {
    text("editor-status", "Fehler: " + error.message);
    toast(error.message, true);
  }
}

function renderConfirmSummary() {
  const signal = state.signals.find((item) => item.id === state.editorSignalId);
  const box = $("confirm-summary");
  if (!signal) { box.textContent = ""; return; }
  const allEvidence = signal.evidence || [];
  const evidence = allEvidence.filter((entry) => !entry.demo);
  const runs = new Set(evidence.map((entry) => entry.run_id).filter(Boolean));
  const actions = new Set(evidence.map((entry) => entry.action_label).filter(Boolean));
  box.innerHTML = "";
  const line = (label, value) => {
    const div = document.createElement("div");
    div.textContent = `${label}: ${value}`;
    box.appendChild(div);
  };
  line("Signal", signal.name);
  line("Status", statusLabel(signal.status));
  line("Unabhaengige Laeufe", runs.size);
  line("Aktionsbezeichnungen", [...actions].join(", ") || "-");
  line("DEMO-Evidenz", allEvidence.some((entry) => entry.demo) ? "ja (Bestaetigung gesperrt)" : "nein");
  line("Bestaetigungsnotiz", signal.confirmed_note || "-");
}

async function confirmSignal() {
  try {
    await api("/api/signals/confirm", {
      method: "POST",
      body: JSON.stringify({
        id: state.editorSignalId,
        note: $("confirm-note").value,
        checklist: $("confirm-checklist").checked,
      }),
    });
    toast("Signal bestaetigt.");
    text("confirm-status", "Bestaetigt.");
    await pollSignals();
  } catch (error) {
    text("confirm-status", "Nicht bestaetigt: " + error.message);
    toast(error.message, true);
  }
}

/* ---------- Referenzen ---------- */

async function loadReferences() {
  if (state.references) { renderReferences(); return; }
  try {
    state.references = await api("/api/references");
    renderReferences();
  } catch (error) { toast(error.message, true); }
}

function renderReferences() {
  if (!state.references) return;
  const sources = $("reference-sources");
  const list = $("reference-list");
  sources.replaceChildren();
  list.replaceChildren();
  for (const source of state.references.sources || []) {
    const item = document.createElement("div");
    item.className = "reference-source";
    const title = document.createElement("div");
    title.style.fontWeight = "700";
    title.textContent = `${source.id} · ${source.source_platform || ""} · ${source.model_year || ""}`;
    const link = document.createElement("a");
    link.href = source.url; link.target = "_blank"; link.rel = "noreferrer"; link.textContent = source.url;
    link.style.color = "var(--accent)";
    const note = document.createElement("div"); note.className = "muted"; note.textContent = source.notes || "";
    const conf = document.createElement("div"); conf.className = "warn"; conf.textContent = "Vertrauen: " + (source.confidence || "-") + " · Ziel-V90: " + (source.target_applicable ? "ja" : "nein");
    item.append(title, link, note, conf);
    sources.appendChild(item);
  }
  for (const hypothesis of state.references.hypotheses || []) {
    const item = document.createElement("div");
    item.className = "reference-item";
    const title = document.createElement("div");
    title.style.fontWeight = "700";
    title.textContent = `${hypothesis.can_id} · ${hypothesis.purpose_hypothesis || ""}`;
    const detail = document.createElement("div");
    detail.className = "muted";
    detail.textContent = `Quelle: ${hypothesis.source_id} · Byte: ${hypothesis.byte ?? "-"} · Bitmaske: ${hypothesis.bit_mask ?? "-"} · Frame: ${hypothesis.extended ? "EXT" : "STD"}`;
    const warn = document.createElement("div");
    warn.className = "warn";
    warn.textContent = "UNVERIFIZIERT · " + (hypothesis.notes || "") + " · Nicht als V90-2021-Definition verwenden.";
    item.append(title, detail, warn);
    list.appendChild(item);
  }
}

/* ---------- Export / Status ---------- */

function renderExportStatus(status) {
  const el = $("export-status");
  el.replaceChildren();
  const add = (label, value) => {
    const k = document.createElement("span"); k.textContent = label;
    const v = document.createElement("b"); v.textContent = value;
    el.append(k, v);
  };
  add("Quelle", status.source);
  add("USB", status.connected ? "verbunden" : "getrennt");
  add("Port", status.serial_port || "-");
  add("Session", status.session.stem);
  add("Messung", status.measurement.active ? status.measurement.name : "-");
  add("Frames", String(status.counters.frames_received));
  add("DEMO-Frames", String(status.counters.demo_frames));
  add("Ignorierte DEMO im Serialmodus", String(status.counters.rejected_demo_frames));
  add("Parse-Fehler", String(status.counters.parse_errors));
  add("Rohzeilen", String(status.counters.raw_lines));
  add("USB-Reconnects", String(status.counters.serial_reconnects));
  const fw = status.firmware_stats || {};
  add("ESP USB-Statistik", fw.tx !== undefined ? `tx=${fw.tx} dropped=${fw.dropped} txerr=${fw.tx_errors} queue=${fw.queue_used}/${fw.queue_capacity}` : "-");
  add("Letzter Frame", status.last_frame.received_iso ? fmtTime(status.last_frame.received_iso) + " (" + fmtAge(status.last_frame.age_ms) + ")" : "-");
  add("Hinweis", status.no_frames_hint || "-");
}

async function refreshExportFiles() {
  try {
    const data = await api("/api/export/list");
    const list = $("measurement-files");
    list.replaceChildren();
    const measurements = (data.files || []).filter((file) => file.name.endsWith(".csv") && !file.name.startsWith("session_"));
    if (measurements.length === 0) {
      const empty = document.createElement("div"); empty.className = "muted"; empty.textContent = "Noch keine Messdateien.";
      list.appendChild(empty);
    }
    for (const file of measurements) {
      const row = document.createElement("div");
      row.className = "file-row";
      const name = document.createElement("span");
      name.textContent = `${file.name} (${Math.round(file.size / 1024)} kB)`;
      const links = document.createElement("span");
      const csv = document.createElement("a");
      csv.href = "/api/export/measurement?name=" + encodeURIComponent(file.name) + "&format=csv";
      csv.textContent = "CSV";
      const json = document.createElement("a");
      json.href = "/api/export/measurement?name=" + encodeURIComponent(file.name) + "&format=json";
      json.textContent = "JSON";
      json.style.marginLeft = "10px";
      links.append(csv, json);
      row.append(name, links);
      list.appendChild(row);
    }
  } catch (error) { toast(error.message, true); }
}

async function pollRawFrames() {
  try {
    const data = await api("/api/frames?limit=50");
    const body = $("raw-frames");
    body.replaceChildren();
    for (const frame of (data.frames || []).slice().reverse()) {
      const tr = document.createElement("tr");
      const values = [fmtTime(frame.received_iso), frame.id_hex || ("0x" + Number(frame.id).toString(16).toUpperCase()), frame.extended ? "EXT" : "STD", String(frame.dlc), frame.data, frame.demo ? "DEMO" : ""];
      for (const value of values) {
        const td = document.createElement("td");
        td.textContent = value;
        tr.appendChild(td);
      }
      body.appendChild(tr);
    }
  } catch (_) { /* Status zeigt Fehler */ }
}

/* ---------- Live-CAN-Monitor ---------- */

function monitorDataFilter(frame) {
  const needle = $("monitor-filter-data").value.replace(/[^0-9A-Fa-f]/g, "").toUpperCase();
  if (!needle) return true;
  const data = String(frame.data || "").replace(/[^0-9A-Fa-f]/g, "").toUpperCase();
  return data.includes(needle);
}

function scheduleMonitorReload() {
  if (state.monitorFilterTimer) clearTimeout(state.monitorFilterTimer);
  state.monitorFilterTimer = setTimeout(() => pollMonitor(true), 250);
}

async function pollMonitor(reset = false) {
  if (state.monitorBusy) return;
  if (state.monitorPaused && !reset) return;
  if (reset) {
    state.monitorFrames = [];
    state.monitorLastSeq = 0;
    state.monitorRates = new Map();
    state.monitorMissed = 0;
    $("monitor-frames").replaceChildren();
  }
  state.monitorBusy = true;
  try {
    const id = $("monitor-filter-id").value.trim();
    const type = $("monitor-filter-type").value;
    const data = await api(`/api/monitor?since=${state.monitorLastSeq}&limit=300&id=${encodeURIComponent(id)}&type=${encodeURIComponent(type)}`);
    state.monitorStatus = data;
    state.monitorMissed += Number(data.missed_frames || 0);
    const seen = new Set(state.monitorFrames.map((frame) => Number(frame.monitor_seq)));
    for (const frame of (data.frames || [])) {
      const key = Number(frame.monitor_seq);
      if (!seen.has(key)) { state.monitorFrames.push(frame); seen.add(key); }
    }
    state.monitorFrames.sort((a, b) => Number(a.monitor_seq) - Number(b.monitor_seq));
    if (state.monitorFrames.length > 800) state.monitorFrames = state.monitorFrames.slice(-800);
    state.monitorLastSeq = Number(data.latest_seq) || state.monitorLastSeq;
    state.monitorRates = new Map((data.rates || []).map((entry) => [Number(entry.id), Number(entry.rate)]));
    renderMonitor();
  } catch (error) {
    const el = $("monitor-stats");
    el.replaceChildren();
    const message = document.createElement("div");
    message.className = "monitor-stat bad";
    message.textContent = "Monitor nicht erreichbar: " + error.message;
    el.appendChild(message);
  } finally {
    state.monitorBusy = false;
  }
}

function renderMonitor() {
  const data = state.monitorStatus || {};
  const stats = $("monitor-stats");
  stats.replaceChildren();
  const add = (label, value, bad = false) => {
    const box = document.createElement("div");
    box.className = "monitor-stat" + (bad ? " bad" : "");
    const key = document.createElement("span"); key.textContent = label;
    const val = document.createElement("strong"); val.textContent = value;
    box.append(key, val);
    stats.appendChild(box);
  };
  const fw = data.firmware_stats || {};
  add("Quelle", data.demo_mode ? "DEMO (synthetisch)" : "USB-CDC");
  add("USB", data.connected || data.demo_mode ? "verbunden" : "getrennt", !data.connected && !data.demo_mode);
  add("Nachrichten/s", Number(data.total_rate || 0).toFixed(1));
  add("Aktive IDs (2 s)", String(data.unique_ids || 0));
  add("Frames gesamt", String((data.counters || {}).frames_received || 0));
  add("Aufzeichnung", data.measurement?.active ? data.measurement.name : "aus");
  add("Parse-Fehler", String((data.counters || {}).parse_errors || 0), Number((data.counters || {}).parse_errors || 0) > 0);
  add("ESP USB-Verluste", fw.dropped !== undefined ? `tx=${fw.tx} dropped=${fw.dropped} txerr=${fw.tx_errors}` : "-");
  add("Anzeige-Luecken", String(state.monitorMissed));
  show("monitor-demo-badge", Boolean(data.demo_mode));
  $("monitor-record-start").disabled = Boolean(data.measurement?.active);
  $("monitor-record-stop").disabled = !data.measurement?.active;

  const body = $("monitor-frames");
  body.replaceChildren();
  const rows = state.monitorFrames.filter(monitorDataFilter).slice(-300).reverse();
  const fragment = document.createDocumentFragment();
  for (const frame of rows) {
    const tr = document.createElement("tr");
    const canId = Number(frame.id);
    const idText = frame.id_hex || ("0x" + canId.toString(16).toUpperCase().padStart(frame.extended ? 8 : 3, "0"));
    const rate = state.monitorRates.get(canId);
    const values = [
      fmtTime(frame.received_iso),
      String(frame.monitor_seq ?? "-"),
      idText,
      frame.extended ? "EXT" : "STD",
      String(frame.dlc),
      String(frame.data || ""),
      rate !== undefined ? rate.toFixed(1) : "-",
      frame.demo ? "DEMO" : "",
    ];
    for (const value of values) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    }
    if (frame.demo) tr.classList.add("demo-row");
    fragment.appendChild(tr);
  }
  body.appendChild(fragment);
}

async function monitorRecordStart() {
  const name = $("monitor-measurement").value.trim() || "live_monitor";
  try {
    const data = await api("/api/measurement/start", { method: "POST", body: JSON.stringify({ name }) });
    $("monitor-measurement").value = "";
    toast("Aufzeichnung gestartet: " + data.measurement);
    await pollStatus();
    await pollMonitor();
  } catch (error) { toast(error.message, true); }
}

async function monitorRecordStop() {
  try {
    const data = await api("/api/measurement/stop", { method: "POST", body: "{}" });
    toast("Aufzeichnung gestoppt: " + data.measurement);
    await pollStatus();
    await refreshExportFiles();
    await pollMonitor();
  } catch (error) { toast(error.message, true); }
}

/* ---------- Messung / Events ---------- */

async function startMeasurement() {
  const custom = $("measurement-custom").value.trim();
  const name = custom || $("measurement-select").value;
  if (!name) { toast("Kein Messungsname", true); return; }
  try {
    const data = await api("/api/measurement/start", { method: "POST", body: JSON.stringify({ name }) });
    toast("Messung gestartet: " + data.measurement);
    $("measurement-custom").value = "";
    await pollStatus();
  } catch (error) { toast(error.message, true); }
}

async function stopMeasurement() {
  try {
    const data = await api("/api/measurement/stop", { method: "POST", body: "{}" });
    toast("Messung gestoppt: " + data.measurement);
    await pollStatus();
    await refreshExportFiles();
  } catch (error) { toast(error.message, true); }
}

async function canAction(action) {
  if (action === "start") {
    const ok = window.confirm(
      "Live-Empfang jetzt starten?\n\n" +
      "Nur LISTEN_ONLY, fest 500 kbit/s, kein Scan, kein Auto-Neustart.\n" +
      "Bei Fahrzeugstoerungen sofort CAN STOP oder USB trennen."
    );
    if (!ok) return;
  }
  try {
    const endpoint = action === "start" ? "/api/can/start" : "/api/can/stop";
    await api(endpoint, { method: "POST", body: "{}" });
    toast(action === "start" ? "CAN START gesendet (LISTEN_ONLY, 500 kbit/s)." : "CAN STOP gesendet.");
    await pollStatus();
  } catch (error) { toast(error.message, true); }
}

async function markEvent() {
  const label = $("event-label").value.trim();
  if (!label) { toast("Ereignis-Text fehlt", true); return; }
  try {
    await api("/api/event/mark", { method: "POST", body: JSON.stringify({ label }) });
    $("event-label").value = "";
    toast("Ereignis markiert.");
    await pollEvents();
  } catch (error) { toast(error.message, true); }
}

/* ---------- Init ---------- */

function init() {
  initTabs();
  $("live-signal").addEventListener("change", (event) => { state.selectedSignal = event.target.value; renderLive(); });
  $("editor-select").addEventListener("change", (event) => { state.editorSignalId = event.target.value; populateEditor(); });
  $("editor-save").addEventListener("click", saveEditor);
  $("editor-reload").addEventListener("click", populateEditor);
  $("editor-testing").addEventListener("click", async () => {
    try {
      await api("/api/signals/status", { method: "POST", body: JSON.stringify({ id: state.editorSignalId, status: "testing" }) });
      toast("Signal auf IN PRUEFUNG gesetzt.");
      await pollSignals();
    } catch (error) { toast(error.message, true); }
  });
  $("editor-reject").addEventListener("click", async () => {
    try {
      await api("/api/signals/status", { method: "POST", body: JSON.stringify({ id: state.editorSignalId, status: "rejected" }) });
      toast("Signal als verworfen markiert.");
      await pollSignals();
    } catch (error) { toast(error.message, true); }
  });
  $("confirm-button").addEventListener("click", confirmSignal);
  $("confirm-reset").addEventListener("click", () => {
    $("confirm-note").value = "";
    $("confirm-checklist").checked = false;
    text("confirm-status", "");
    renderConfirmSummary();
  });

  $("assistant-start").addEventListener("click", () => assistantAction("/api/assistant/start", { action_label: $("assistant-action").value.trim() }));
  $("assistant-mark").addEventListener("click", () => assistantAction("/api/assistant/mark_action", { action_label: $("assistant-action").value.trim() }));
  $("assistant-evaluate").addEventListener("click", () => assistantAction("/api/assistant/evaluate"));
  $("assistant-reset").addEventListener("click", () => assistantAction("/api/assistant/reset"));

  $("measurement-start").addEventListener("click", startMeasurement);
  $("measurement-stop").addEventListener("click", stopMeasurement);
  $("event-mark").addEventListener("click", markEvent);
  $("can-start").addEventListener("click", () => canAction("start"));
  $("can-stop").addEventListener("click", () => canAction("stop"));
  $("demo-toggle").addEventListener("click", async () => {
    try {
      const data = await api("/api/demo/toggle", { method: "POST", body: "{}" });
      toast("Demo-Aktion: " + (data.demo_flag ? "EIN" : "AUS"));
      await pollStatus();
    } catch (error) { toast(error.message, true); }
  });
  $("live-on").addEventListener("click", () => {
    const signal = state.signals.find((item) => item.id === state.selectedSignal);
    $("event-label").value = (signal?.name || "Signal") + ": Aktion EIN";
    markEvent();
  });
  $("live-off").addEventListener("click", () => {
    const signal = state.signals.find((item) => item.id === state.selectedSignal);
    $("event-label").value = (signal?.name || "Signal") + ": Aktion AUS";
    markEvent();
  });
  $("measurement-refresh").addEventListener("click", refreshExportFiles);
  $("monitor-filter-id").addEventListener("input", scheduleMonitorReload);
  $("monitor-filter-type").addEventListener("change", scheduleMonitorReload);
  $("monitor-filter-data").addEventListener("input", renderMonitor);
  $("monitor-pause").addEventListener("click", () => {
    state.monitorPaused = !state.monitorPaused;
    $("monitor-pause").textContent = state.monitorPaused ? "Fortsetzen" : "Pause";
    if (!state.monitorPaused) pollMonitor();
  });
  $("monitor-clear").addEventListener("click", () => {
    state.monitorFrames = [];
    state.monitorMissed = 0;
    $("monitor-frames").replaceChildren();
  });
  $("monitor-record-start").addEventListener("click", monitorRecordStart);
  $("monitor-record-stop").addEventListener("click", monitorRecordStop);
  $("monitor-files").addEventListener("click", () => tabTo("export"));

  pollStatus();
  pollSignals();
  pollEvents();
  pollAssistant();
  refreshExportFiles();
  pollRawFrames();
  setInterval(pollStatus, 1000);
  setInterval(pollSignals, 1200);
  setInterval(pollEvents, 1000);
  setInterval(() => { if ($("tab-assistant").classList.contains("active")) pollAssistant(); }, 600);
  setInterval(() => { if ($("tab-monitor").classList.contains("active")) pollMonitor(); }, 500);
  setInterval(() => { if ($("tab-export").classList.contains("active")) { refreshExportFiles(); pollRawFrames(); } }, 3000);
}

document.addEventListener("DOMContentLoaded", () => {
  init();
  const hash = location.hash.replace("#", "");
  if (hash && document.querySelector(`.tab[data-tab="${hash}"]`)) tabTo(hash);
});
