#pragma once

#include <cstddef>
#include <cstdint>
#include <cstdio>

#include "volvo_core/can_frame.h"

namespace volvo {

// Klar definiertes NDJSON-Format fuer CAN-Nutzdaten auf USB-CDC und TCP.
// Diagnosemeldungen werden NICHT als "type":"can" gesendet, sondern mit
// dem Praefix "# " (siehe UsbLogger::diag).
inline size_t formatCanNdjson(const CanFrame& frame, char* out, size_t out_size) {
  if (out == nullptr || out_size == 0) return 0;
  char data_hex[17];
  for (size_t i = 0; i < kMaxDataBytes; ++i) {
    std::snprintf(&data_hex[i * 2], 3, "%02X", frame.data[i]);
  }
  data_hex[16] = '\0';

  char id_hex[12];
  std::snprintf(id_hex, sizeof(id_hex), frame.extended ? "0x%08X" : "0x%03X",
                static_cast<unsigned>(frame.id));

  int written = std::snprintf(
      out, out_size,
      "{\"type\":\"can\",\"seq\":%u,\"timestamp_us\":%llu,\"id\":%u,"
      "\"id_hex\":\"%s\",\"extended\":%s,\"dlc\":%u,\"data\":\"%s\","
      "\"demo\":%s}\n",
      static_cast<unsigned>(frame.seq),
      static_cast<unsigned long long>(frame.timestamp_us),
      static_cast<unsigned>(frame.id), id_hex,
      frame.extended ? "true" : "false", static_cast<unsigned>(frame.dlc),
      data_hex, frame.demo ? "true" : "false");
  if (written < 0) return 0;
  return static_cast<size_t>(written);
}

}  // namespace volvo
