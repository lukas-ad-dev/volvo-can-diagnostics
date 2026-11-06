#include "web_server.h"

#include <WiFi.h>
#include <esp_heap_caps.h>

#include <cstdio>
#include <cstring>

#include "app_config.h"
#include "volvo_core/csv.h"
#include "volvo_core/id_stats.h"
#include "web_ui.h"
#include "usb_logger.h"

namespace volvo {
namespace {

CompareResult g_compare;

void formatIdHex(uint32_t id, bool extended, char* out, size_t out_size) {
  std::snprintf(out, out_size, extended ? "0x%08X" : "0x%03X",
                static_cast<unsigned>(id));
}

void formatDataHex(const uint8_t* data, uint8_t dlc, char* out, size_t out_size) {
  if (out_size < 17) {
    if (out_size > 0) out[0] = '\0';
    return;
  }
  for (size_t i = 0; i < kMaxDataBytes; ++i) {
    if (i < dlc) {
      std::snprintf(&out[i * 2], 3, "%02X", data[i]);
    } else {
      out[i * 2] = '0';
      out[i * 2 + 1] = '0';
    }
  }
  out[16] = '\0';
}

void formatBitsHex(const uint8_t* data, char* out, size_t out_size) {
  formatDataHex(data, kMaxDataBytes, out, out_size);
}

bool isFinite(double value) {
  return value == value && value > -1e100 && value < 1e100;
}

}  // namespace

void WebServerApp::begin(Settings* settings, CanManager* can, OutputControl* outputs,
                         PowerManager* power) {
  settings_ = settings;
  can_ = can;
  outputs_ = outputs;
  power_ = power;

  server_.on("/", HTTP_GET, [this]() { handleIndex(); });
  server_.on("/style.css", HTTP_GET, [this]() { handleStyle(); });
  server_.on("/app.js", HTTP_GET, [this]() { handleScript(); });
  server_.on("/favicon.ico", HTTP_GET, [this]() { handleFavicon(); });
  server_.on("/api/status", HTTP_GET, [this]() { handleStatus(); });
  server_.on("/api/messages", HTTP_GET, [this]() { handleMessages(); });
  server_.on("/api/stats", HTTP_GET, [this]() { handleStats(); });
  server_.on("/api/settings", HTTP_POST, [this]() { handleSettings(); });
  server_.on("/api/phase", HTTP_POST, [this]() { handlePhase(); });
  server_.on("/api/compare", HTTP_GET, [this]() { handleCompare(); });
  server_.on("/api/compare/export", HTTP_GET, [this]() { handleCompareExport(); });
  server_.on("/api/record", HTTP_POST, [this]() { handleRecord(); });
  server_.on("/api/export/csv", HTTP_GET, [this]() { handleExportCsv(); });
  server_.on("/api/export/json", HTTP_GET, [this]() { handleExportJson(); });
  server_.on("/api/clear", HTTP_POST, [this]() { handleClear(); });
  server_.onNotFound([this]() { handleNotFound(); });
  server_.begin();
  usbLogger().diag("WEB", "HTTP auf http://%s/", WiFi.softAPIP().toString().c_str());
}

void WebServerApp::loop() { server_.handleClient(); }

void WebServerApp::sendJson(const JsonDocument& document, int code) {
  String payload;
  serializeJson(document, payload);
  server_.sendHeader("Cache-Control", "no-store");
  server_.send(code, "application/json; charset=utf-8", payload);
}

void WebServerApp::sendError(int code, const char* message) {
  JsonDocument document;
  document["ok"] = false;
  document["error"] = message;
  sendJson(document, code);
}

void WebServerApp::sendText(int code, const char* content_type, const char* text) {
  server_.sendHeader("Cache-Control", "no-store");
  server_.send(code, content_type, text);
}

void WebServerApp::addDownloadHeader(const char* filename) {
  char header[192];
  std::snprintf(header, sizeof(header), "attachment; filename=\"%s\"", filename);
  server_.sendHeader("Content-Disposition", header);
  server_.sendHeader("Cache-Control", "no-store");
}

void WebServerApp::handleIndex() {
  server_.sendHeader("Cache-Control", "no-store");
  server_.send_P(200, "text/html; charset=utf-8", VOLVO_INDEX_HTML);
}

void WebServerApp::handleStyle() {
  server_.sendHeader("Cache-Control", "no-store");
  server_.send_P(200, "text/css; charset=utf-8", VOLVO_STYLE_CSS);
}

void WebServerApp::handleScript() {
  server_.sendHeader("Cache-Control", "no-store");
  server_.send_P(200, "application/javascript; charset=utf-8", VOLVO_APP_JS);
}

void WebServerApp::handleFavicon() { server_.send(204, "text/plain", ""); }

void WebServerApp::handleStatus() {
  CanStatus status;
  can_->fillStatus(status);

  JsonDocument document;
  document["ok"] = true;
  document["demo"] = status.demo_mode;
  document["source"] = status.source_name;
  document["driver_state"] = status.driver_state_name;
  document["bitrate_kbps"] = status.bitrate_kbps;
  document["total_frames"] = status.total_frames;
  document["unique_ids"] = status.unique_ids;
  document["msgs_per_sec"] = status.msgs_per_sec;
  document["dropped_live"] = status.dropped_live;
  document["dropped_capture"] = status.dropped_capture;
  document["twai_errors"] = status.twai_errors;
  document["rx_queue_full"] = status.rx_queue_full;
  document["latest_seq"] = status.latest_seq;
  document["uptime_ms"] = status.uptime_ms;
  document["free_heap"] = status.free_heap;
  document["free_psram"] = status.free_psram;
  document["recording"] = status.recording;
  document["capture_count"] = status.capture_count;
  document["capture_capacity"] = status.capture_capacity;
  document["capture_dropped"] = status.capture_dropped;

  JsonObject phases = document["phases"].to<JsonObject>();
  JsonObject a = phases["a"].to<JsonObject>();
  a["active"] = status.phase_a_active;
  a["valid"] = status.phase_a_valid;
  a["frames"] = status.phase_a_frames;
  a["duration_ms"] = status.phase_a_duration_ms;
  JsonObject b = phases["b"].to<JsonObject>();
  b["active"] = status.phase_b_active;
  b["valid"] = status.phase_b_valid;
  b["frames"] = status.phase_b_frames;
  b["duration_ms"] = status.phase_b_duration_ms;

  JsonObject settings = document["settings"].to<JsonObject>();
  settings["bitrate_kbps"] = status.bitrate_kbps;
  settings["demo"] = status.demo_mode;

  JsonObject ap = document["ap"].to<JsonObject>();
  ap["ssid"] = kApSsid;
  ap["ip"] = WiFi.softAPIP().toString();

  JsonObject output = document["output"].to<JsonObject>();
  output["hardware_enabled"] = false;
  output["safe"] = true;

  JsonObject power = document["power"].to<JsonObject>();
  power["state"] = power_ != nullptr ? power_->stateName() : "ACTIVE";

  UsbLoggerStats usb = usbLogger().stats();
  JsonObject usb_doc = document["usb"].to<JsonObject>();
  usb_doc["tx_frames"] = usb.tx_frames;
  usb_doc["dropped"] = usb.dropped;
  usb_doc["tx_errors"] = usb.tx_errors;
  usb_doc["diag_dropped"] = usb.diag_dropped;
  usb_doc["queue_used"] = usb.queue_used;
  usb_doc["queue_capacity"] = usb.queue_capacity;

  sendJson(document);
}

void WebServerApp::handleMessages() {
  uint32_t since = 0;
  if (server_.hasArg("since")) since = static_cast<uint32_t>(server_.arg("since").toInt());
  size_t limit = kMaxHttpMessages;
  if (server_.hasArg("limit")) {
    long requested = server_.arg("limit").toInt();
    if (requested > 0) limit = static_cast<size_t>(requested);
  }
  if (limit > kMaxHttpMessages) limit = kMaxHttpMessages;

  static CanFrame frames[kMaxHttpMessages];
  static IdAggregate stats[kMaxIds];

  uint32_t latest = 0;
  uint32_t dropped = 0;
  size_t count = can_->getMessagesSince(since, frames, limit, latest, dropped);
  size_t stats_count = can_->getIdStats(stats, kMaxIds);

  JsonDocument document;
  document["ok"] = true;
  document["latest_seq"] = latest;
  document["dropped"] = dropped;
  JsonArray messages = document["messages"].to<JsonArray>();
  for (size_t i = 0; i < count; ++i) {
    const CanFrame& frame = frames[i];
    double frequency = 0.0;
    for (size_t j = 0; j < stats_count; ++j) {
      if (stats[j].id == frame.id && stats[j].extended == frame.extended) {
        uint64_t duration = stats[j].last_us > stats[j].first_us
                                ? stats[j].last_us - stats[j].first_us
                                : 0;
        if (duration < 1000000ULL) duration = 1000000ULL;
        frequency = IdStats::frequencyHz(stats[j].count, duration);
        break;
      }
    }
    JsonObject item = messages.add<JsonObject>();
    char id_hex[12];
    char data_hex[17];
    formatIdHex(frame.id, frame.extended, id_hex, sizeof(id_hex));
    formatDataHex(frame.data, frame.dlc, data_hex, sizeof(data_hex));
    item["seq"] = frame.seq;
    item["timestamp_us"] = frame.timestamp_us;
    item["id"] = frame.id;
    item["id_hex"] = id_hex;
    item["extended"] = frame.extended;
    item["dlc"] = frame.dlc;
    item["data"] = data_hex;
    item["demo"] = frame.demo;
    item["freq_hz"] = frequency;
  }
  sendJson(document);
}

void WebServerApp::handleStats() {
  static IdAggregate stats[kMaxIds];
  size_t count = can_->getIdStats(stats, kMaxIds);
  CanStatus status;
  can_->fillStatus(status);

  JsonDocument document;
  document["ok"] = true;
  document["latest_seq"] = status.latest_seq;
  JsonArray ids = document["ids"].to<JsonArray>();
  for (size_t i = 0; i < count; ++i) {
    const IdAggregate& entry = stats[i];
    uint64_t duration = entry.last_us > entry.first_us ? entry.last_us - entry.first_us : 0;
    if (duration < 1000000ULL) duration = 1000000ULL;
    uint64_t now_us = static_cast<uint64_t>(status.uptime_ms) * 1000ULL;
    uint64_t age_ms = now_us > entry.last_us ? (now_us - entry.last_us) / 1000ULL : 0;
    char id_hex[12];
    char data_hex[17];
    formatIdHex(entry.id, entry.extended, id_hex, sizeof(id_hex));
    formatDataHex(entry.last_data, entry.max_dlc, data_hex, sizeof(data_hex));
    JsonObject item = ids.add<JsonObject>();
    item["id"] = entry.id;
    item["id_hex"] = id_hex;
    item["extended"] = entry.extended;
    item["count"] = entry.count;
    item["freq_hz"] = IdStats::frequencyHz(entry.count, duration);
    item["payload_changes"] = entry.payload_changes;
    item["last_seen_ms"] = age_ms;
    item["data"] = data_hex;
    item["demo"] = entry.demo;
  }
  sendJson(document);
}

void WebServerApp::handleSettings() {
  JsonDocument input;
  DeserializationError error = deserializeJson(input, server_.arg("plain"));
  if (error) {
    sendError(400, "Ungueltiges JSON");
    return;
  }
  uint32_t bitrate = input["bitrate"] | 0U;
  bool demo = input["demo"] | false;
  if (!Settings::isSupportedBitrate(bitrate)) {
    sendError(400, "Nur 500 kbit/s (fester Testbetrieb) ist erlaubt");
    return;
  }
  if (!can_->requestBitrate(bitrate)) {
    sendError(503, "Quelle ist belegt; bitte erneut versuchen");
    return;
  }
  if (!can_->requestDemo(demo)) {
    sendError(503, "Demo-Umschaltung konnte nicht eingereiht werden");
    return;
  }
  JsonDocument document;
  document["ok"] = true;
  document["bitrate"] = bitrate;
  document["demo"] = demo;
  document["note"] = "Einstellungen gespeichert. CAN bleibt aus; START ist bis zur Hardwarefreigabe gesperrt.";
  sendJson(document);
}

void WebServerApp::handlePhase() {
  JsonDocument input;
  DeserializationError error = deserializeJson(input, server_.arg("plain"));
  if (error) {
    sendError(400, "Ungueltiges JSON");
    return;
  }
  String action = input["action"] | "";
  String phase = input["phase"] | "";
  bool ok = false;
  String message;

  if (action == "reset") {
    can_->phaseReset();
    ok = true;
  } else if (phase == "A" || phase == "B") {
    if (action == "start") {
      ok = can_->phaseStart(phase[0]);
      if (!ok) message = "Phase konnte nicht gestartet werden (andere Phase laeuft?)";
    } else if (action == "stop") {
      ok = can_->phaseStop(phase[0]);
      if (!ok) message = "Phase ist nicht aktiv";
    } else {
      message = "Unbekannte Aktion";
    }
  } else {
    message = "Phase muss A oder B sein";
  }

  JsonDocument document;
  document["ok"] = ok;
  if (!ok) document["error"] = message.length() > 0 ? message : "Aktion nicht moeglich";
  sendJson(document, ok ? 200 : 409);
}

void WebServerApp::handleCompare() {
  can_->compare(g_compare);
  streamCompareJson(g_compare, false);
}

void WebServerApp::handleCompareExport() {
  String format = server_.arg("format");
  can_->compare(g_compare);
  if (!g_compare.ok) {
    sendError(409, "Vergleich nicht verfuegbar: Phase A und B muessen Daten enthalten");
    return;
  }
  if (format == "json") {
    streamCompareJson(g_compare, true);
  } else {
    streamCompareCsv(g_compare);
  }
}

void WebServerApp::handleRecord() {
  JsonDocument input;
  DeserializationError error = deserializeJson(input, server_.arg("plain"));
  if (error) {
    sendError(400, "Ungueltiges JSON");
    return;
  }
  String action = input["action"] | "";
  bool recording = can_->isRecording();
  bool ok = false;
  String message;

  if (action == "start") {
    if (recording) {
      message = "Aufzeichnung laeuft bereits";
    } else {
      ok = can_->recordStart();
      if (!ok) message = "Aufzeichnungspuffer nicht verfuegbar";
    }
  } else if (action == "stop") {
    if (!recording) {
      message = "Aufzeichnung laeuft nicht";
    } else {
      ok = can_->recordStop();
    }
  } else {
    message = "Unbekannte Aktion";
  }

  JsonDocument document;
  document["ok"] = ok;
  if (!ok) document["error"] = message;
  sendJson(document, ok ? 200 : 409);
}

void WebServerApp::handleExportCsv() {
  if (can_->isRecording()) {
    sendError(409, "Aufzeichnung zuerst stoppen, dann exportieren");
    return;
  }
  CanStatus status;
  can_->fillStatus(status);
  if (status.capture_capacity == 0 || status.capture_count == 0) {
    sendError(409, "Keine Aufzeichnung vorhanden");
    return;
  }
  size_t bytes = static_cast<size_t>(status.capture_capacity) * sizeof(CanFrame);
  CanFrame* snapshot = static_cast<CanFrame*>(
      heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (snapshot == nullptr) {
    snapshot = static_cast<CanFrame*>(heap_caps_malloc(bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  }
  if (snapshot == nullptr) {
    sendError(500, "Nicht genug Speicher fuer den Export");
    return;
  }
  uint32_t dropped = 0;
  size_t count = can_->captureSnapshot(snapshot, status.capture_capacity, dropped);
  if (count == 0) {
    heap_caps_free(snapshot);
    sendError(409, "Keine Aufzeichnung vorhanden");
    return;
  }
  addDownloadHeader("volvo-can-aufzeichnung.csv");
  streamCaptureCsv(snapshot, count, dropped);
  heap_caps_free(snapshot);
}

void WebServerApp::handleExportJson() {
  if (can_->isRecording()) {
    sendError(409, "Aufzeichnung zuerst stoppen, dann exportieren");
    return;
  }
  CanStatus status;
  can_->fillStatus(status);
  if (status.capture_capacity == 0 || status.capture_count == 0) {
    sendError(409, "Keine Aufzeichnung vorhanden");
    return;
  }
  size_t bytes = static_cast<size_t>(status.capture_capacity) * sizeof(CanFrame);
  CanFrame* snapshot = static_cast<CanFrame*>(
      heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (snapshot == nullptr) {
    snapshot = static_cast<CanFrame*>(heap_caps_malloc(bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  }
  if (snapshot == nullptr) {
    sendError(500, "Nicht genug Speicher fuer den Export");
    return;
  }
  uint32_t dropped = 0;
  size_t count = can_->captureSnapshot(snapshot, status.capture_capacity, dropped);
  if (count == 0) {
    heap_caps_free(snapshot);
    sendError(409, "Keine Aufzeichnung vorhanden");
    return;
  }
  addDownloadHeader("volvo-can-aufzeichnung.json");
  streamCaptureJson(snapshot, count, dropped);
  heap_caps_free(snapshot);
}

void WebServerApp::handleClear() {
  can_->clearMessages();
  CanStatus status;
  can_->fillStatus(status);
  JsonDocument document;
  document["ok"] = true;
  document["latest_seq"] = status.latest_seq;
  sendJson(document);
}

void WebServerApp::handleNotFound() { sendError(404, "Nicht gefunden"); }

void WebServerApp::streamCompareJson(const CompareResult& result, bool download) {
  server_.setContentLength(CONTENT_LENGTH_UNKNOWN);
  if (download) addDownloadHeader("volvo-can-vergleich.json");
  server_.send(200, "application/json; charset=utf-8", "");

  String chunk;
  chunk.reserve(4096);
  auto flush = [this, &chunk]() {
    if (chunk.length() > 0) {
      server_.sendContent(chunk);
      chunk = "";
    }
  };

  chunk += "{\"ok\":";
  chunk += result.ok ? "true" : "false";
  chunk += ",\"demo\":";
  chunk += result.demo ? "true" : "false";
  chunk += ",\"truncated\":";
  chunk += result.truncated ? "true" : "false";
  chunk += ",\"duration_a_ms\":";
  chunk += String(static_cast<unsigned long>(result.duration_a_us / 1000ULL));
  chunk += ",\"duration_b_ms\":";
  chunk += String(static_cast<unsigned long>(result.duration_b_us / 1000ULL));
  chunk += ",\"entries\":[";

  for (size_t i = 0; i < result.entry_count; ++i) {
    if (i > 0) chunk += ",";
    const CompareEntry& entry = result.entries[i];
    JsonDocument item_doc;
    JsonObject item = item_doc.to<JsonObject>();
    char id_hex[12];
    char data_a[17];
    char data_b[17];
    formatIdHex(entry.id, entry.extended, id_hex, sizeof(id_hex));
    formatDataHex(entry.data_a, entry.dlc_a, data_a, sizeof(data_a));
    formatDataHex(entry.data_b, entry.dlc_b, data_b, sizeof(data_b));
    item["id"] = entry.id;
    item["id_hex"] = id_hex;
    item["extended"] = entry.extended;
    item["in_a"] = entry.in_a;
    item["in_b"] = entry.in_b;
    item["demo"] = entry.demo;
    item["count_a"] = entry.count_a;
    item["count_b"] = entry.count_b;
    item["freq_a"] = isFinite(entry.freq_a) ? entry.freq_a : 0.0;
    item["freq_b"] = isFinite(entry.freq_b) ? entry.freq_b : 0.0;
    item["freq_delta_pct"] = isFinite(entry.freq_delta_pct) ? entry.freq_delta_pct : 0.0;
    item["dlc_a"] = entry.dlc_a;
    item["dlc_b"] = entry.dlc_b;
    item["data_a"] = data_a;
    item["data_b"] = data_b;
    item["payload_changed"] = entry.payload_changed;
    item["frequency_changed"] = entry.frequency_changed;

    JsonArray changed = item["changed_bytes"].to<JsonArray>();
    for (size_t byte = 0; byte < kMaxDataBytes; ++byte) {
      if (entry.changed_bits[byte] == 0) continue;
      JsonObject change = changed.add<JsonObject>();
      char a_hex[3];
      char b_hex[3];
      char xor_hex[3];
      std::snprintf(a_hex, sizeof(a_hex), "%02X", entry.data_a[byte]);
      std::snprintf(b_hex, sizeof(b_hex), "%02X", entry.data_b[byte]);
      std::snprintf(xor_hex, sizeof(xor_hex), "%02X", entry.changed_bits[byte]);
      change["index"] = byte;
      change["a"] = a_hex;
      change["b"] = b_hex;
      change["xor"] = xor_hex;
    }

    JsonArray variable_a = item["variable_a"].to<JsonArray>();
    JsonArray variable_b = item["variable_b"].to<JsonArray>();
    for (size_t byte = 0; byte < kMaxDataBytes; ++byte) {
      char a_hex[3];
      char b_hex[3];
      std::snprintf(a_hex, sizeof(a_hex), "%02X", entry.variable_a[byte]);
      std::snprintf(b_hex, sizeof(b_hex), "%02X", entry.variable_b[byte]);
      variable_a.add(a_hex);
      variable_b.add(b_hex);
    }

    String item_json;
    serializeJson(item_doc, item_json);
    chunk += item_json;
    if (chunk.length() > 4096) flush();
  }

  chunk += "]}";
  flush();
  server_.sendContent("");
}

void WebServerApp::streamCompareCsv(const CompareResult& result) {
  server_.setContentLength(CONTENT_LENGTH_UNKNOWN);
  addDownloadHeader("volvo-can-vergleich.csv");
  server_.send(200, "text/csv; charset=utf-8", "");

  String chunk;
  chunk.reserve(4096);
  auto flush = [this, &chunk]() {
    if (chunk.length() > 0) {
      server_.sendContent(chunk);
      chunk = "";
    }
  };

  chunk += "can_id,extended,in_a,in_b,count_a,count_b,freq_a,freq_b,freq_delta_pct,dlc_a,dlc_b,data_a,data_b,changed_mask,changed_bits,variable_a,variable_b,demo,payload_changed,frequency_changed\n";

  for (size_t i = 0; i < result.entry_count; ++i) {
    const CompareEntry& entry = result.entries[i];
    char id_hex[12];
    char data_a[17];
    char data_b[17];
    char bits[17];
    char variable_a[17];
    char variable_b[17];
    char line[320];
    formatIdHex(entry.id, entry.extended, id_hex, sizeof(id_hex));
    formatDataHex(entry.data_a, entry.dlc_a, data_a, sizeof(data_a));
    formatDataHex(entry.data_b, entry.dlc_b, data_b, sizeof(data_b));
    formatBitsHex(entry.changed_bits, bits, sizeof(bits));
    formatBitsHex(entry.variable_a, variable_a, sizeof(variable_a));
    formatBitsHex(entry.variable_b, variable_b, sizeof(variable_b));
    std::snprintf(line, sizeof(line),
                  "%s,%u,%u,%u,%u,%u,%.3f,%.3f,%.2f,%u,%u,%s,%s,%02X,%s,%s,%s,%u,%u,%u\n",
                  id_hex, entry.extended ? 1U : 0U, entry.in_a ? 1U : 0U,
                  entry.in_b ? 1U : 0U, static_cast<unsigned>(entry.count_a), static_cast<unsigned>(entry.count_b),
                  entry.freq_a, entry.freq_b, entry.freq_delta_pct, entry.dlc_a,
                  entry.dlc_b, data_a, data_b, entry.changed_mask, bits,
                  variable_a, variable_b, entry.demo ? 1U : 0U,
                  entry.payload_changed ? 1U : 0U, entry.frequency_changed ? 1U : 0U);
    chunk += line;
    if (chunk.length() > 4096) flush();
  }
  flush();
  server_.sendContent("");
}

void WebServerApp::streamCaptureCsv(CanFrame* frames, size_t count, uint32_t dropped) {
  (void)dropped;
  server_.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server_.send(200, "text/csv; charset=utf-8", "");

  String chunk;
  chunk.reserve(4096);
  auto flush = [this, &chunk]() {
    if (chunk.length() > 0) {
      server_.sendContent(chunk);
      chunk = "";
    }
  };
  char line[160];
  formatCsvHeader(line, sizeof(line));
  chunk += line;
  for (size_t i = 0; i < count; ++i) {
    formatCsvFrame(frames[i], line, sizeof(line));
    chunk += line;
    if (chunk.length() > 4096) flush();
  }
  flush();
  server_.sendContent("");
}

void WebServerApp::streamCaptureJson(CanFrame* frames, size_t count, uint32_t dropped) {
  (void)dropped;
  server_.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server_.send(200, "application/json; charset=utf-8", "");

  String chunk;
  chunk.reserve(4096);
  auto flush = [this, &chunk]() {
    if (chunk.length() > 0) {
      server_.sendContent(chunk);
      chunk = "";
    }
  };
  chunk += "[";
  for (size_t i = 0; i < count; ++i) {
    const CanFrame& frame = frames[i];
    char id_hex[12];
    char data_hex[17];
    char line[240];
    formatIdHex(frame.id, frame.extended, id_hex, sizeof(id_hex));
    formatDataHex(frame.data, frame.dlc, data_hex, sizeof(data_hex));
    std::snprintf(line, sizeof(line),
                  "%s{\"seq\":%u,\"timestamp_us\":%llu,\"id\":%u,\"id_hex\":\"%s\","
                  "\"extended\":%s,\"dlc\":%u,\"data\":\"%s\",\"demo\":%s}",
                  i == 0 ? "" : ",", static_cast<unsigned>(frame.seq),
                  static_cast<unsigned long long>(frame.timestamp_us),
                  static_cast<unsigned>(frame.id), id_hex,
                  frame.extended ? "true" : "false", static_cast<unsigned>(frame.dlc),
                  data_hex, frame.demo ? "true" : "false");
    chunk += line;
    if (chunk.length() > 4096) flush();
  }
  chunk += "]";
  flush();
  server_.sendContent("");
}

}  // namespace volvo
