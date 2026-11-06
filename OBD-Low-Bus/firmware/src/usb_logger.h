#pragma once

#include <Arduino.h>
#include <atomic>

#include "volvo_core/can_frame.h"

namespace volvo {

struct UsbLoggerStats {
  uint32_t tx_frames = 0;
  uint32_t dropped = 0;
  uint32_t tx_errors = 0;
  uint32_t diag_dropped = 0;
  uint32_t queue_used = 0;
  uint32_t queue_capacity = 0;
};

// Kontinuierlicher USB-CDC-NDJSON-Logger.
// CAN-Daten werden ueber eine eigene Queue von der Empfangsaufgabe
// entkoppelt; die eigentliche USB-Ausgabe laeuft in einem eigenen Task.
// Diagnosezeilen beginnen mit "# " und sind damit klar von CAN-JSON
// unterscheidbar. Es wird nie blockierend auf USB gewartet.
class UsbLogger {
 public:
  void begin();
  bool enqueue(const CanFrame& frame);
  void diag(const char* tag, const char* fmt, ...);
  void discardQueued();
  UsbLoggerStats stats() const;

 private:
  static void taskEntry(void* arg);
  void taskLoop();
  bool writeLine(const char* line, size_t length, TickType_t lock_timeout);

  QueueHandle_t queue_ = nullptr;
  SemaphoreHandle_t write_mutex_ = nullptr;
  TaskHandle_t task_ = nullptr;
  std::atomic<uint32_t> tx_frames_{0};
  std::atomic<uint32_t> dropped_{0};
  std::atomic<uint32_t> tx_errors_{0};
  std::atomic<uint32_t> diag_dropped_{0};
};

UsbLogger& usbLogger();

}  // namespace volvo
