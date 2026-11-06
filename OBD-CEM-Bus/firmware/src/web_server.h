#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WebServer.h>

#include "can_manager.h"
#include "output_control.h"
#include "power_manager.h"
#include "settings.h"

namespace volvo {

class WebServerApp {
 public:
  void begin(Settings* settings, CanManager* can, OutputControl* outputs, PowerManager* power);
  void loop();

 private:
  void handleIndex();
  void handleStyle();
  void handleScript();
  void handleStatus();
  void handleMessages();
  void handleStats();
  void handleSettings();
  void handlePhase();
  void handleCompare();
  void handleCompareExport();
  void handleRecord();
  void handleExportCsv();
  void handleExportJson();
  void handleClear();
  void handleFavicon();
  void handleNotFound();

  void sendJson(const JsonDocument& document, int code = 200);
  void sendError(int code, const char* message);
  void sendText(int code, const char* content_type, const char* text);
  void streamCompareJson(const CompareResult& result, bool download);
  void streamCompareCsv(const CompareResult& result);
  void streamCaptureCsv(CanFrame* frames, size_t count, uint32_t dropped);
  void streamCaptureJson(CanFrame* frames, size_t count, uint32_t dropped);
  void addDownloadHeader(const char* filename);

  WebServer server_{kHttpPort};
  Settings* settings_ = nullptr;
  CanManager* can_ = nullptr;
  OutputControl* outputs_ = nullptr;
  PowerManager* power_ = nullptr;
};

}  // namespace volvo
