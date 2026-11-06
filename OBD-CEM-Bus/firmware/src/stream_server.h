#pragma once

#include <Arduino.h>
#include <WiFi.h>

#include "app_config.h"
#include "can_manager.h"

namespace volvo {

// NDJSON-Stream auf TCP-Port 81 fuer den Python-Collector unter Windows.
// Der Stream ist unabhaengig von der Ringpuffer-Aufzeichnung und sendet
// ausschliesslich empfangene bzw. klar als DEMO markierte Frames.
class StreamServer {
 public:
  void begin(CanManager* can);
  void loop();

 private:
  static void taskEntry(void* arg);
  void taskLoop();
  void sendFrame(WiFiClient& client, const CanFrame& frame);

  WiFiServer server_{kStreamPort};
  CanManager* can_ = nullptr;
  TaskHandle_t task_handle_ = nullptr;

  WiFiClient clients_[kMaxStreamClients];
  uint32_t last_seq_[kMaxStreamClients] = {0};
};

}  // namespace volvo
