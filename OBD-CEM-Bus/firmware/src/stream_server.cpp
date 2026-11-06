#include "stream_server.h"

#include <cstdio>

#include "usb_logger.h"

namespace volvo {
namespace {

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

}  // namespace

void StreamServer::begin(CanManager* can) {
  can_ = can;
  server_.begin();
  server_.setNoDelay(true);
  xTaskCreatePinnedToCore(taskEntry, "canstream", kStreamTaskStack, this, 2, &task_handle_, 0);
  usbLogger().diag("STREAM", "NDJSON auf TCP-Port %u", kStreamPort);
}

void StreamServer::taskEntry(void* arg) {
  static_cast<StreamServer*>(arg)->taskLoop();
}

void StreamServer::taskLoop() {
  for (;;) {
    WiFiClient incoming = server_.accept();
    if (incoming) {
      for (size_t i = 0; i < kMaxStreamClients; ++i) {
        if (!clients_[i] || !clients_[i].connected()) {
          clients_[i] = incoming;
          clients_[i].setNoDelay(true);
          CanStatus status;
          can_->fillStatus(status);
          last_seq_[i] = status.latest_seq;
          usbLogger().diag("STREAM", "Client %u verbunden; startet bei seq %u",
                           static_cast<unsigned>(i), static_cast<unsigned>(last_seq_[i]));
          break;
        }
      }
    }

    CanFrame frames[64];
    for (size_t i = 0; i < kMaxStreamClients; ++i) {
      if (!clients_[i] || !clients_[i].connected()) continue;
      uint32_t latest = 0;
      uint32_t dropped = 0;
      size_t count = can_->getMessagesSince(last_seq_[i], frames, 64, latest, dropped);
      for (size_t j = 0; j < count; ++j) {
        sendFrame(clients_[i], frames[j]);
        if (frames[j].seq > last_seq_[i]) last_seq_[i] = frames[j].seq;
      }
      if (count == 0 && latest > last_seq_[i] + 1024) {
        last_seq_[i] = latest - 1024;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(40));
  }
}

void StreamServer::sendFrame(WiFiClient& client, const CanFrame& frame) {
  char id_hex[12];
  char data_hex[17];
  char line[224];
  formatIdHex(frame.id, frame.extended, id_hex, sizeof(id_hex));
  formatDataHex(frame.data, frame.dlc, data_hex, sizeof(data_hex));
  int length = std::snprintf(
      line, sizeof(line),
      "{\"seq\":%u,\"timestamp_us\":%llu,\"id\":%u,\"id_hex\":\"%s\","
      "\"extended\":%s,\"dlc\":%u,\"data\":\"%s\",\"demo\":%s}\n",
      static_cast<unsigned>(frame.seq),
      static_cast<unsigned long long>(frame.timestamp_us),
      static_cast<unsigned>(frame.id), id_hex, frame.extended ? "true" : "false",
      static_cast<unsigned>(frame.dlc), data_hex, frame.demo ? "true" : "false");
  if (length <= 0) return;
  if (client.write(reinterpret_cast<const uint8_t*>(line), static_cast<size_t>(length)) == 0) {
    client.stop();
  }
}

}  // namespace volvo
