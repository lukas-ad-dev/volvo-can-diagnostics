#include "usb_logger.h"

#include <cstdarg>
#include <cstdio>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

#include "app_config.h"
#include "volvo_core/ndjson.h"

namespace volvo {

UsbLogger& usbLogger() {
  static UsbLogger instance;
  return instance;
}

void UsbLogger::begin() {
  if (queue_ != nullptr) return;
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);
  // Groesserer USB-CDC-TX-Puffer gegen Burst-Verluste bei hoher Buslast.
  Serial.setTxBufferSize(8192);
  write_mutex_ = xSemaphoreCreateMutex();
  queue_ = xQueueCreate(kUsbLoggerQueueLength, sizeof(CanFrame));
  if (write_mutex_ == nullptr || queue_ == nullptr) {
    Serial.printf("# [USB] Initialisierung fehlgeschlagen\n");
    return;
  }
  xTaskCreatePinnedToCore(taskEntry, "usbcan", kUsbLoggerTaskStack, this, 2, &task_, 0);
  diag("USB", "NDJSON-Logger aktiv; CAN-Frames type=can, Diagnose mit #");
}

bool UsbLogger::enqueue(const CanFrame& frame) {
  if (queue_ == nullptr) return false;
  if (xQueueSend(queue_, &frame, 0) == pdTRUE) return true;
  ++dropped_;
  return false;
}

void UsbLogger::taskEntry(void* arg) {
  static_cast<UsbLogger*>(arg)->taskLoop();
}

void UsbLogger::taskLoop() {
  uint32_t last_stats_ms = 0;
  for (;;) {
    // Ohne USB-Host nicht in den leeren CDC-Puffer schreiben. Die Queue
    // puffert bis zur Verbindung; volle Queue wird als dropped gezaehlt.
    if (!Serial) {
      vTaskDelay(pdMS_TO_TICKS(100));
      continue;
    }

    CanFrame frame;
    if (xQueueReceive(queue_, &frame, pdMS_TO_TICKS(100)) == pdTRUE) {
      char line[256];
      size_t length = formatCanNdjson(frame, line, sizeof(line));
      bool ok = length > 0 && writeLine(line, length, pdMS_TO_TICKS(20));
      if (ok) {
        ++tx_frames_;
      } else {
        ++dropped_;
      }
    }

    uint32_t now = millis();
    if (now - last_stats_ms >= 30000) {
      last_stats_ms = now;
      UsbLoggerStats current = stats();
      diag("USB-STATS", "tx=%u dropped=%u txerr=%u diagdrop=%u queue=%u/%u",
           static_cast<unsigned>(current.tx_frames),
           static_cast<unsigned>(current.dropped),
           static_cast<unsigned>(current.tx_errors),
           static_cast<unsigned>(current.diag_dropped),
           static_cast<unsigned>(current.queue_used),
           static_cast<unsigned>(current.queue_capacity));
    }
  }
}

bool UsbLogger::writeLine(const char* line, size_t length, TickType_t lock_timeout) {
  if (write_mutex_ == nullptr || line == nullptr || length == 0) return false;
  if (xSemaphoreTake(write_mutex_, lock_timeout) != pdTRUE) return false;
  bool ok = false;
  int available = Serial.availableForWrite();
  if (available >= static_cast<int>(length)) {
    size_t written = Serial.write(reinterpret_cast<const uint8_t*>(line), length);
    if (written == length) {
      ok = true;
    } else {
      ++tx_errors_;
    }
  }
  xSemaphoreGive(write_mutex_);
  return ok;
}

void UsbLogger::discardQueued() {
  if (queue_ == nullptr) return;
  uint32_t count = uxQueueMessagesWaiting(queue_);
  if (count > 0) {
    xQueueReset(queue_);
    dropped_ += count;
  }
}

void UsbLogger::diag(const char* tag, const char* fmt, ...) {
  if (write_mutex_ == nullptr) return;
  char message[192];
  va_list args;
  va_start(args, fmt);
  vsnprintf(message, sizeof(message), fmt, args);
  va_end(args);

  char line[256];
  int length = std::snprintf(line, sizeof(line), "# [%s] %s\n", tag != nullptr ? tag : "DIAG", message);
  if (length <= 0) return;
  if (!writeLine(line, static_cast<size_t>(length), pdMS_TO_TICKS(10))) {
    ++diag_dropped_;
  }
}

UsbLoggerStats UsbLogger::stats() const {
  UsbLoggerStats result;
  result.tx_frames = tx_frames_.load();
  result.dropped = dropped_.load();
  result.tx_errors = tx_errors_.load();
  result.diag_dropped = diag_dropped_.load();
  result.queue_used = queue_ != nullptr ? uxQueueMessagesWaiting(queue_) : 0;
  result.queue_capacity = queue_ != nullptr ? kUsbLoggerQueueLength : 0;
  return result;
}

}  // namespace volvo
